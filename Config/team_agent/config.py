# ── config.py — Central configuration constants for the team_agent system ────

import os
import itertools
from dotenv import load_dotenv

load_dotenv()

# ── API Groq — désactivé temporairement, utilisation d'OpenRouter ────────────
_GROQ_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
    os.getenv("GROQ_API_KEY_5"),
] if k]

# ── API Cerebras ───────────────────────────────────────────────────────────────
CEREBRAS_API_KEY  = os.getenv("Cerebras_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OpenRouter_API_KEY", "")

if CEREBRAS_API_KEY:
    os.environ["OPENAI_API_KEY"] = CEREBRAS_API_KEY
    os.environ["OPENAI_API_BASE"] = "https://api.cerebras.ai/v1"
    print(f"[config] Cerebras      : ok ({CEREBRAS_API_KEY[:12]}...)")
elif OPENROUTER_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
    os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
    print(f"[config] OpenRouter    : ok ({OPENROUTER_API_KEY[:12]}...)")
elif _GROQ_KEYS:
    os.environ["GROQ_API_KEY"] = _GROQ_KEYS[0]
    print(f"[config] Groq keys     : {len(_GROQ_KEYS)} clé(s) chargée(s)")
else:
    raise ValueError("Aucune clé API trouvée — définir Cerebras_API_KEY, OpenRouter_API_KEY ou GROQ_API_KEY dans .env")

# ── Rotation Groq (conservée pour réactivation future) ───────────────────────
if _GROQ_KEYS:
    _key_cycle = itertools.cycle(_GROQ_KEYS)

    def next_groq_key() -> str:
        key = next(_key_cycle)
        os.environ["GROQ_API_KEY"] = key
        return key

# ── Modèles ───────────────────────────────────────────────────────────────────
# Cerebras : llama3.1-8b (60K TPM) pour tâches légères, qwen-3-235b (30K TPM) pour raisonnement
SIMPLE_MODEL   = "llama3.1-8b"                    # 60K TPM/min — recall, remember, writeup, analyst
COMPLEX_MODEL  = "qwen-3-235b-a22b-instruct-2507" # 30K TPM/min — planner, architect, dev, test, reviewer
MEDIUM_MODEL   = "qwen-3-235b-a22b-instruct-2507" # 30K TPM/min — debug
MODEL_PROVIDER = "openai"                # Cerebras = API compatible OpenAI
OPENROUTER_MODELS: list[str] = []        # désactivé

print(f"[config] Simple model  : {SIMPLE_MODEL}")
print(f"[config] Complex model : {COMPLEX_MODEL}")
print(f"[config] Provider      : {MODEL_PROVIDER}")
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
