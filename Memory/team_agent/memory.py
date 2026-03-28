# ── memory.py — Multi-layer memory access (L2 Redis · L3 ChromaDB · L4 Postgres) ────

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy service clients — imported only when first used so the module loads
# even when services are offline (graceful degradation).
# ---------------------------------------------------------------------------


def _redis_client():
    try:
        import redis
        from Config.team_agent.config import REDIS_URL
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as exc:
        logger.warning("L2 Redis unavailable: %s", exc)
        return None


_chroma_cache: tuple | None = None

def _chroma_collection():
    global _chroma_cache
    if _chroma_cache is not None:
        return _chroma_cache
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        from Config.team_agent.config import (
            CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION, EMBEDDING_MODEL,
        )
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(CHROMA_COLLECTION)
        encoder = SentenceTransformer(EMBEDDING_MODEL)
        _chroma_cache = (collection, encoder)
        return _chroma_cache
    except Exception as exc:
        logger.warning("L3 ChromaDB unavailable: %s", exc)
        return None, None


def _pg_conn():
    try:
        import psycopg2
        from Config.team_agent.config import PG_DSN
        return psycopg2.connect(PG_DSN)
    except Exception as exc:
        logger.warning("L4 Postgres unavailable: %s", exc)
        return None


# ---------------------------------------------------------------------------
# L2 — Redis working memory
# ---------------------------------------------------------------------------

def l2_save(content: str, category: str = "general") -> bool:
    """Save content to Redis with a TTL-based expiry."""
    try:
        from Config.team_agent.config import L2_TTL_SECONDS
        r = _redis_client()
        if r is None:
            return False
        key = f"team_agent:memory:{category}:{int(time.time())}"
        r.setex(key, L2_TTL_SECONDS, json.dumps({"content": content, "category": category}))
        return True
    except Exception as exc:
        logger.warning("l2_save failed: %s", exc)
        return False


def l2_search(query: str, k: int = 5) -> list[Document]:
    """Retrieve recent Redis entries whose content contains the query terms."""
    try:
        r = _redis_client()
        if r is None:
            return []
        keys = r.keys("team_agent:memory:*")
        docs: list[Document] = []
        for key in keys:
            raw = r.get(key)
            if raw and query.lower() in raw.lower():
                data = json.loads(raw)
                docs.append(Document(
                    page_content=data["content"],
                    metadata={"layer": "L2", "category": data.get("category", "")},
                ))
        return docs[:k]
    except Exception as exc:
        logger.warning("l2_search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# L3 — ChromaDB long-term memory
# ---------------------------------------------------------------------------

def l3_save(content: str, category: str = "general") -> bool:
    """Embed and persist content to ChromaDB when novelty threshold is met."""
    try:
        from Config.team_agent.config import L3_WRITE_THRESHOLD
        collection, encoder = _chroma_collection()
        if collection is None:
            return False
        embedding = encoder.encode(content).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=1)
        distances = results.get("distances", [[]])[0]
        if distances and distances[0] < L3_WRITE_THRESHOLD:
            return False  # Too similar to existing entry — skip
        doc_id = f"{category}_{int(time.time())}"
        collection.add(ids=[doc_id], embeddings=[embedding],
                       documents=[content], metadatas=[{"category": category}])
        return True
    except Exception as exc:
        logger.warning("l3_save failed: %s", exc)
        return False


def l3_search(query: str, k: int = 5) -> list[Document]:
    """Semantic search over ChromaDB long-term memory."""
    try:
        collection, encoder = _chroma_collection()
        if collection is None:
            return []
        embedding = encoder.encode(query).tolist()
        results = collection.query(query_embeddings=[embedding], n_results=k)
        docs: list[Document] = []
        for doc, meta in zip(results.get("documents", [[]])[0],
                              results.get("metadatas", [[]])[0]):
            docs.append(Document(
                page_content=doc,
                metadata={"layer": "L3", "category": meta.get("category", "")},
            ))
        return docs
    except Exception as exc:
        logger.warning("l3_search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# L4 — Postgres identity / preference memory
# ---------------------------------------------------------------------------

def l4_save(content: str, category: str = "preference", confidence: float = 0.9) -> bool:
    """Persist a high-confidence belief to the Postgres memory_facts table."""
    try:
        conn = _pg_conn()
        if conn is None:
            return False
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO memory_facts (content, category, confidence) "
                    "VALUES (%s, %s, %s)",
                    (content, category, confidence),
                )
        conn.close()
        return True
    except Exception as exc:
        logger.warning("l4_save failed: %s", exc)
        return False


def l4_search(query: str, k: int = 5) -> list[Document]:
    """Full-text search over Postgres memory_facts (active entries only)."""
    try:
        conn = _pg_conn()
        if conn is None:
            return []
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, content, category FROM memory_facts "
                    "WHERE is_active = TRUE AND content ILIKE %s "
                    "ORDER BY (confidence * 0.5 + LEAST(usage_count, 20) * 0.025) DESC "
                    "LIMIT %s",
                    (f"%{query}%", k),
                )
                rows = cur.fetchall()
                # Increment usage_count for returned facts
                if rows:
                    ids = [r[0] for r in rows]
                    cur.execute(
                        "UPDATE memory_facts SET usage_count = usage_count + 1, "
                        "last_used = NOW() WHERE id = ANY(%s)",
                        (ids,),
                    )
        conn.close()
        return [
            Document(page_content=r[1], metadata={"layer": "L4", "category": r[2]})
            for r in rows
        ]
    except Exception as exc:
        logger.warning("l4_search failed: %s", exc)
        return []


def l4_compact() -> str:
    """Report active vs total entry counts in memory_facts (maintenance utility)."""
    try:
        conn = _pg_conn()
        if conn is None:
            return "L4 Postgres unavailable."
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FILTER (WHERE is_active), COUNT(*) FROM memory_facts"
                )
                active, total = cur.fetchone()
        conn.close()
        return f"L4 memory_facts: {active} active / {total} total entries."
    except Exception as exc:
        logger.warning("l4_compact failed: %s", exc)
        return "L4 compact failed."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_to_memory(content: str, category: str = "general") -> dict:
    """Save content to all available memory layers."""
    return {
        "L2": l2_save(content, category),
        "L3": l3_save(content, category),
    }


def search_memory(query: str, k: int = 5) -> list[Document]:
    """Hybrid search across L4 > L3 > L2, deduplicated by content."""
    seen: set[str] = set()
    results: list[Document] = []
    for doc in l4_search(query, k) + l3_search(query, k) + l2_search(query, k):
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            results.append(doc)
        if len(results) >= k:
            break
    return results


def commit_to_identity(content: str, category: str = "preference",
                        confidence: float = 0.9) -> bool:
    """Commit a high-confidence insight to L4 identity store."""
    return l4_save(content, category, confidence)
