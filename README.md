# Agentic Architect

Système multi-agents IA (LangGraph) avec mémoire persistante, interface React + FastAPI WebSocket.

---

## Prérequis système

Installer **uniquement** ces deux outils sur la machine — tout le reste (Node.js, npm, packages Python) vit dans le venv :

| Outil | Pourquoi |
|---|---|
| Python 3.11+ | Runtime pour créer le venv |
| Docker & Docker Compose | Bases de données (Redis, ChromaDB, PostgreSQL) |

---

## Installation (une seule fois)

### 1. Créer le venv Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Installer Node.js dans le venv

Node.js et npm sont isolés dans le venv via `nodeenv` — **rien n'est installé globalement**.

```bash
.venv\Scripts\pip install nodeenv
.venv\Scripts\nodeenv --node=22.14.0 --prebuilt .venv\node
```

### 3. Installer les dépendances frontend

```bash
cd App\team_agent\ui
..\..\..\..\.venv\node\Scripts\npm.cmd install
cd ..\..\..
```

### 4. Variables d'environnement

Copie `.env.example` en `.env` et renseigne :

```env
# API principale (OpenAI-compatible)
Cerebras_API_KEY="csk-..."
# ou
OpenRouter_API_KEY="sk-or-..."

# Mémoire — laisser par défaut avec docker-compose
REDIS_URL=redis://localhost:6379
CHROMA_HOST=localhost
CHROMA_PORT=8002
PG_DSN=postgresql://planner:planner_secret@localhost:5432/planner_memory
```

### 5. Modèles

Dans [Config/team_agent/config.py](Config/team_agent/config.py) :

```python
SIMPLE_MODEL   = "llama3.1-8b"                    # tâches légères
COMPLEX_MODEL  = "qwen-3-235b-a22b-instruct-2507" # tâches complexes
MODEL_PROVIDER = "openai"                          # API OpenAI-compatible
```

### Autres paramètres disponibles

| Variable | Défaut | Description |
|---|---|---|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Modèle d'embeddings |
| `WORKSPACE_DIR` | `./workspace` | Répertoire de travail des agents |
| `SHELL_TIMEOUT_SECONDS` | `60` | Timeout commandes shell |
| `L2_TTL_SECONDS` | `86400` | TTL cache Redis (L2) |
| `CHROMA_COLLECTION` | `team_agent_longterm` | Collection ChromaDB (L3) |

---

## Lancement

### 1. Démarrer les bases de données

```bash
docker-compose up -d
```

Lance Redis (6379), ChromaDB (8002), PostgreSQL (5432).

### 2. Démarrer l'application

```bat
start.bat    # Lance le backend FastAPI + le frontend React
stop.bat     # Arrête tout
```

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Frontend UI | http://localhost:5173 |
| RedisInsight | http://localhost:8001 |
| ChromaDB | http://localhost:8002 |

---

## Architecture

```
Agents/              → 9 agents (supervisor, planner, architect, dev, reviewer, test, debug, writeup, analyst)
Config/              → Configuration centralisée
Graph/               → Graphe LangGraph (StateGraph + MemorySaver)
Memory/              → Backends mémoire (L2 Redis, L3 ChromaDB, L4 PostgreSQL)
Tools/               → Outils partagés (fichiers, git, shell, mémoire, tool_loop)
App/
  team_agent/
    server.py        → Backend FastAPI WebSocket + endpoint HTTP /result/{thread_id}
    ui/              → Frontend React + Vite + Tailwind
workspace/           → Fichiers produits par les agents
workspace/traces/    → Traces JSON + Markdown exportées après chaque run
```

### Couches mémoire

| Niveau | Backend | Port | Usage |
|---|---|---|---|
| L2 | Redis | 6379 | Mémoire de session (TTL 24h) |
| L3 | ChromaDB | 8002 | Mémoire long-terme sémantique |
| L4 | PostgreSQL | 5432 | Identité et décisions persistantes |

---

## Interface

L'UI React se connecte au backend via WebSocket (`ws://localhost:5173/ws` → proxy Vite → `ws://localhost:8000/ws`).
Les events du graphe LangGraph sont streamés en temps réel vers 4 onglets :

| Onglet | Contenu |
|---|---|
| 💬 Chat | Messages des agents + live trace pendant le run |
| 📊 Sequence Diagram | Diagramme Mermaid de la séquence d'agents (mis à jour live) |
| 🔬 Agent Trace (v1) | Record JSON complet (tokens par agent, fichiers, git SHA) |
| 📋 Event Log | Log filtrable par agent et type — click sur une ligne pour le payload complet |

### Event Log — types d'events

| Type | Icône | Détail affiché |
|---|---|---|
| `llm_call` | 🔵 | Modèle, itération, tokens in/out/total, aperçu du prompt |
| `llm_response` | 🟢 | Aperçu de la réponse, présence de tool calls |
| `tool_call` | 🟡 | Nom de l'outil, résumé des arguments |
| `tool_result` | 🟠 | Résultat de l'outil (100 premiers caractères) |
| `memory_op` | 🟣 | Opération (inject/recall/remember), layer L2/L3/L4, query, nb docs |
| `supervisor_route` | 🎯 | Agent cible du routage |
| `agent_start` | ▶ | Début d'exécution de l'agent |
| `agent_done` | ✅ | Durée d'exécution en ms |
| `error` | ❌ | Message d'erreur |

---

## Tracer — agent_trace

Le système de trace est basé sur **[TracerIA](https://github.com/Velkasi/TracerIA)** (`agent_trace`), situé dans `../04_Tracer/`.

Chaque run produit automatiquement :
- **Streaming temps réel** — events envoyés via WebSocket à chaque nœud LangGraph
- **Export JSON** — `workspace/traces/{id}_trace.json`
- **Export Markdown** — `workspace/traces/{id}_trace.md` (sequence diagram + token summary + event log complet)
- **Endpoint HTTP** — `GET /result/{thread_id}` pour récupérer le record complet

```python
# Cycle de vie par run (géré automatiquement par tool_loop.py)
reset_builder(workspace_dir, task, session_id)          # début du run
get_builder().agent_start(agent)
get_builder().llm_call(agent, model, tokens, prompt_preview)
get_builder().llm_response(agent, has_tool_calls, response_preview)
get_builder().tool_call(agent, tool_name, args)
get_builder().tool_result(agent, tool_name, result)
get_builder().memory_op(agent, operation, layer, summary, query, results_count)
get_builder().agent_done(agent, duration_ms)
record = get_builder().build_record(files_written)      # fin du run
```
