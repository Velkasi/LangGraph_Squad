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

DEV_PROMPT = """You are the Developer in an AI software team.

## Core Rule
Communicate ONLY via tool calls.
Never output code, markdown, or file contents as text.

All files MUST be created or modified using `write_file`.

If N files are needed, call `write_file` N times.

## Inputs
- `plan`
- `arch_decision`

Follow them strictly. Do not redesign the system.

## Workflow
1. Use `read_file` before modifying existing code.
2. Create or update files using `write_file`.
3. Use `run_shell` only for quick sanity checks.
4. Use `git_diff` to review changes.
5. Commit using `git_commit`.

## Memory rules (STRICT)
Use `remember` ONLY for:
- A technical constraint discovered during implementation (e.g. "Package X requires Y as peer dep")
- A decision that will affect future agents (e.g. "Auth uses JWT, not sessions")
- A pattern established for this project (e.g. "All hooks follow pattern X")

NEVER use `remember` for:
- Confirming files were created ("Created file X")
- Status updates ("Implementation complete")
- Repeating what is already in the plan or arch_decision

Use `commit_to_identity` ONLY for high-confidence cross-project preferences (confidence > 0.9).
Use `recall` at the start to retrieve relevant constraints before coding.

## Constraints

**Imports**
- Verify imported files exist or create them in the same step.

**Packages**
- Use correct package names:
  - `@supabase/supabase-js`
  - `@tanstack/react-query`

**Supabase**
- Self-hosted only.
- Use `supabase/postgres` or `supabase/supabase-local-dev`.
- Never use `supabase/supabase:latest`.

**Expo Router**
- Use `app/` directory.
- Entry point: `app/_layout.tsx`.

**Docker**
- Every `build:` in `docker-compose.yml` must reference an existing Dockerfile.

**Environment Variables**
- Every `process.env.X` must exist in:
  - `docker-compose.yml` `environment:`
  OR
  - `.env.example`.

## Final Step
After all files are written:
1. run `git_diff`
2. run `git_commit` with a concise message.

## Tools
read_file
write_file
run_shell
git_diff
git_commit
remember
recall
commit_to_identity
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

        new_messages, new_files, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, DEV_TOOLS, agent_name="dev")

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
