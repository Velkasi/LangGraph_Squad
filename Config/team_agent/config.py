# ── config.py — Central configuration constants for the team_agent system ────

import os
import itertools
from dotenv import load_dotenv

load_dotenv()

# ── API Groq — jusqu'à 5 clés en rotation pour maximiser le quota ────────────
_GROQ_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
    os.getenv("GROQ_API_KEY_5"),
] if k]

if not _GROQ_KEYS:
    raise ValueError("Au moins une clé GROQ_API_KEY requise dans .env")

_key_cycle = itertools.cycle(_GROQ_KEYS)

def next_groq_key() -> str:
    """Retourne la prochaine clé Groq en rotation round-robin."""
    key = next(_key_cycle)
    os.environ["GROQ_API_KEY"] = key
    return key

def rotate_on_error() -> str:
    """Force la rotation vers la clé suivante après une erreur 413/429."""
    key = next(_key_cycle)
    os.environ["GROQ_API_KEY"] = key
    logger_msg = f"[config] Rotation vers clé : {key[:8]}..."
    print(logger_msg)
    return key

# Initialise avec la première clé
os.environ["GROQ_API_KEY"] = _GROQ_KEYS[0]
GROQ_API_KEY = _GROQ_KEYS[0]

print(f"[config] Groq keys     : {len(_GROQ_KEYS)} clé(s) chargée(s)")
for i, k in enumerate(_GROQ_KEYS, 1):
    print(f"[config]   key {i}       : ok ({k[:8]}...)")

# ── Modèles ───────────────────────────────────────────────────────────────────
# llama-4-scout : 30K TPM / 30 RPM  → tâches légères, meilleur débit token
# qwen3-32b     :  6K TPM / 60 RPM  → raisonnement complexe, tool calling
# gpt-oss-120b  :  8K TPM / 30 RPM  → tâches intermédiaires (optionnel)
SIMPLE_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"  # 30K TPM — recall, remember, writeup
COMPLEX_MODEL  = "qwen/qwen3-32b"                              # 6K TPM  — plan, arch, dev, test, review
MEDIUM_MODEL   = "moonshotai/kimi-k1.5-32b"                     # 8K TPM  — debug, analyst
MODEL_PROVIDER = "groq"
print(f"[config] Simple model  : {SIMPLE_MODEL}")
print(f"[config] Complex model : {COMPLEX_MODEL}")
print(f"[config] Medium model  : {MEDIUM_MODEL}")
print(f"[config] Provider      : {MODEL_PROVIDER}")

# ── Memory / Redis (L2) ───────────────────────────────────────────────────────
REDIS_URL      = os.getenv("REDIS_URL", "redis://localhost:6379")
L2_TTL_SECONDS = int(os.getenv("L2_TTL_SECONDS", "86400"))
print(f"[config] Redis (L2)    : {REDIS_URL}  TTL={L2_TTL_SECONDS}s")

# ── Memory / ChromaDB (L3) ────────────────────────────────────────────────────
CHROMA_HOST       = os.getenv("CHROMA_HOST",       "localhost")
CHROMA_PORT       = int(os.getenv("CHROMA_PORT",   "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "team_agent_longterm")
L3_WRITE_THRESHOLD         = float(os.getenv("L3_WRITE_THRESHOLD",         "0.25"))
L3_CONTRADICTION_THRESHOLD = float(os.getenv("L3_CONTRADICTION_THRESHOLD", "0.92"))
print(f"[config] Chroma (L3)   : {CHROMA_HOST}:{CHROMA_PORT}  collection={CHROMA_COLLECTION}")

# ── Memory / Postgres (L4 identity) ──────────────────────────────────────────
PG_DSN = os.getenv(
    "PG_DSN",
    "postgresql://planner:planner_secret@localhost:5432/planner_memory",
)
_pg_log = PG_DSN.split("@")[-1] if "@" in PG_DSN else PG_DSN
print(f"[config] Postgres (L4) : {_pg_log}")

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
print(f"[config] Embeddings    : {EMBEDDING_MODEL}")

# ── Workspace ─────────────────────────────────────────────────────────────────
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "./workspace")
print(f"[config] Workspace     : {WORKSPACE_DIR}")

# ── Shell ─────────────────────────────────────────────────────────────────────
SHELL_TIMEOUT_SECONDS = int(os.getenv("SHELL_TIMEOUT_SECONDS", "60"))
print(f"[config] Shell timeout : {SHELL_TIMEOUT_SECONDS}s")

INTERRUPT_BEFORE: list[str] = []

print("[config] Configuration chargée avec succès ✓")
