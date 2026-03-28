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

Lance Redis (6379), ChromaDB (8000), PostgreSQL (5432).

### 2. Démarrer l'application

```bat
start.bat    # Lance le backend FastAPI + le frontend React
stop.bat     # Arrête tout
```

- Backend API : http://localhost:8000
- Frontend UI : http://localhost:5173

---

## Architecture

```
Agents/              → 9 agents (planner, architect, dev, reviewer, test, debug, writeup, analyst, supervisor)
Config/              → Configuration centralisée
Graph/               → Graphe LangGraph
Memory/              → Backends mémoire (L2 Redis, L3 ChromaDB, L4 PostgreSQL)
Tools/               → Outils partagés (fichiers, git, shell, mémoire)
App/
  team_agent/
    server.py        → Backend FastAPI WebSocket
    ui/              → Frontend React + Vite + Tailwind
```

### Couches mémoire

| Niveau | Backend | Usage |
|---|---|---|
| L2 | Redis | Mémoire de session (TTL 24h) |
| L3 | ChromaDB | Mémoire long-terme sémantique |
| L4 | PostgreSQL | Identité et décisions persistantes |

### Interface

L'UI React se connecte au backend via WebSocket (`ws://localhost:8000/ws`).
Les events du graphe LangGraph sont streamés en temps réel vers 4 onglets :

| Onglet | Contenu |
|---|---|
| 💬 Chat | Messages des agents + live trace pendant le run |
| 📊 Sequence Diagram | Diagramme Mermaid de la séquence d'agents |
| 🔬 Agent Trace (v1) | Record JSON complet (tokens, fichiers, git SHA) |
| 📋 Event Log | Log filtrable de tous les events LangGraph |
