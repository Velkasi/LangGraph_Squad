# ── dev.py — Developer agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import COMPLEX_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file, write_file
from Tools.team_agent.git_tools import git_commit, git_diff
from Tools.team_agent.memory_tools import commit_to_identity, remember, recall
from Tools.team_agent.shell_tools import run_shell
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

DEV_TOOLS = [read_file, write_file, run_shell, git_diff, git_commit, remember, recall, commit_to_identity]

DEV_PROMPT = """You are the **Developer** in an AI software-development team.

## CRITICAL — How you must work
You communicate ONLY through tool calls. You NEVER output code, markdown, or file contents as text.
Every file you create MUST be written via `write_file`. No exceptions.
If you want to create 5 files, call `write_file` 5 times — one call per file.
Do NOT describe what you would write. Write it.

## Your responsibilities
- Follow the architecture decision (`arch_decision`) and the plan (`plan`) already established.
- Use `read_file` to inspect existing code before editing.
- Call `write_file` for EVERY file — source code, config, Dockerfile, docker-compose.yml, .env.example, README.
- Use `run_shell` for sanity checks only (e.g. `node -e "require('express')"` after npm install).
- Use `git_diff` to review your changes, then `git_commit` to commit them.
- Use `remember` to log every file you create or modify.

## Strict rules
- **NEVER output file contents as text or markdown** — always use `write_file`.
- **Cross-check every import**: before writing a file that imports from another file, verify that target file exists or plan to create it in the same step.
- **Use correct package names**: `@supabase/supabase-js` (not `supabase-js`), `@tanstack/react-query` (not `react-query`).
- **Supabase self-hosted via Docker**: use the official `supabase/postgres` image for PostgreSQL only, or reference the Supabase local dev stack (`supabase/supabase-local-dev`). Never use `supabase/supabase:latest` — it does not exist.
- **Expo Router**: always create `app/` directory with `_layout.tsx` as entry point, not `src/`.
- **Every Dockerfile referenced in docker-compose.yml must be written** — never leave a `build:` directive pointing to a missing Dockerfile.
- **Environment variables**: every `process.env.X` used in code must be declared in `docker-compose.yml` under `environment:` or in a `.env.example` file.
- After writing all files, always call `git_commit` with a concise message.
- Do not make design decisions — those belong to the architect.

## Available tools
read_file · write_file · run_shell · git_diff · git_commit · remember · recall · commit_to_identity
"""


def dev_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=DEV_PROMPT)
        context_parts: list[str] = []
        if state.get("plan"):
            context_parts.append(f"## Current plan\n{state['plan']}")
        if state.get("arch_decision"):
            context_parts.append(f"## Architecture decision\n{state['arch_decision']}")
        if state.get("files_written"):
            context_parts.append(
                "## Files already written\n" + "\n".join(f"- {f}" for f in state["files_written"])
            )

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, new_files, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, DEV_TOOLS)

        existing = list(state.get("files_written") or [])
        for path in new_files:
            if path not in existing:
                existing.append(path)

        wrote_something = len(existing) > len(state.get("files_written") or [])
        return {
            "messages": new_messages,
            "current_agent": "dev",
            "files_written": existing,
            "dev_attempts": 0 if wrote_something else (state.get("dev_attempts") or 0) + 1,
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("dev_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[dev] Error: {exc}")],
            "current_agent": "dev",
            "dev_attempts": (state.get("dev_attempts") or 0) + 1,
            "awaiting_human": False,
        }
