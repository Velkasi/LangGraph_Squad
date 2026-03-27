# ── memory_tools.py — LangChain @tool wrappers for the multi-layer memory system ────

from langchain_core.tools import tool
from Memory.team_agent.memory import (
    save_to_memory,
    search_memory,
    commit_to_identity as _commit,
    l4_compact,
)


@tool
def remember(content: str, category: str = "general") -> str:
    """Save something to working memory (L2) and conditionally to long-term memory (L3).

    Args:
        content: The text to remember.
        category: Semantic category tag (e.g. 'decision', 'code', 'requirement').
    """
    saved = save_to_memory(content, category)
    layers = [k for k, v in saved.items() if v]
    if layers:
        return f"Saved to {', '.join(layers)}: {content[:80]}..."
    return f"Memory services unavailable — could not save: {content[:80]}"


@tool
def recall(query: str, k: int = 5) -> str:
    """Search memory across all layers (L2 working, L3 long-term, L4 identity).

    Args:
        query: Natural-language search query.
        k: Maximum number of results to return.
    """
    results = search_memory(query, k=k)
    if not results:
        return "No relevant memories found."
    lines = []
    for doc in results:
        layer = doc.metadata.get("layer", "?")
        cat = doc.metadata.get("category", "")
        lines.append(f"[{layer}/{cat}] {doc.page_content}")
    return "\n".join(lines)


@tool
def commit_to_identity(content: str, category: str = "preference",
                        confidence: float = 0.9) -> str:
    """Commit a high-confidence insight to the L4 identity store (Postgres).

    Args:
        content: The belief or preference to persist permanently.
        category: Category tag (e.g. 'preference', 'constraint', 'principle').
        confidence: Confidence score between 0 and 1.
    """
    ok = _commit(content, category, confidence)
    if ok:
        return f"Committed to identity [{category}]: {content[:80]}..."
    return "L4 identity store unavailable — commit failed."


@tool
def compact_memory() -> str:
    """Summarise and deduplicate the L4 identity store (maintenance utility)."""
    return l4_compact()
