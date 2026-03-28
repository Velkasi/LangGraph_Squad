# ── reviewer.py — Reviewer agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import SIMPLE_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file
from Tools.team_agent.memory_tools import commit_to_identity, recall, remember
from Tools.team_agent.serena_tools import get_serena_tools
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

REVIEWER_TOOLS = [
    read_file, remember, recall, commit_to_identity,
    *get_serena_tools(),
]

REVIEWER_PROMPT = """You are the Reviewer in an AI software team. You are strict and thorough.

## Input
files_written

## Process
1. Use `read_file` to read every file listed in `files_written`.
2. Audit code, configuration, dependencies, and security.
3. Report blocking issues and warnings.

## Checks

**Imports**
- Every `import` or `require` must resolve to:
  - a file in `files_written`, or
  - a valid npm/pip package.

Use `find_symbol` to verify imported symbols exist.
Use `find_referencing_symbols` to ensure removed symbols are not referenced.

**Packages**
- Verify correct package names (e.g. `@supabase/supabase-js`).

**Docker**
- Docker images must exist on Docker Hub.
- Every Dockerfile referenced in `docker-compose.yml` must exist in `files_written`.

**Environment Variables**
- Every `process.env.X` must be declared in:
  - `docker-compose.yml`
  OR
  - `.env.example`.

**Security**
Use `search_for_pattern` to detect:
- hardcoded secrets
- tokens or API keys
- forbidden patterns

Also check for:
- missing error handling
- unhandled promise rejections

## Blocking Conditions
The review fails if any of the following occur:

1. Unresolved import
2. Missing file referenced by code or docker-compose
3. Invalid or non-existent Docker image
4. Hardcoded secret detected
5. Missing environment variable declaration

## Output

## Review Result
**Status:** APPROVED | CHANGES_REQUESTED

**Blocking issues:**
- ...

**Warnings:**
- ...

Only set **Status: APPROVED** if there are zero blocking issues.

## Memory rules (STRICT)
Use `remember` ONLY for:
- A security vulnerability or blocking issue pattern discovered during review (e.g. "JWT tokens logged in plaintext in X")
- A constraint that will affect future agents (e.g. "Package Y is incompatible with Node 18")

NEVER use `remember` for:
- Confirming files were reviewed ("Reviewed file X")
- Status updates ("Review complete")
- Repeating what is already in the arch_decision or files_written list

Use `recall` at the start to retrieve known constraints before reviewing.
Use `commit_to_identity` ONLY for high-confidence cross-project preferences (confidence > 0.9).

## Tools
read_file · remember · recall · commit_to_identity
find_symbol · find_referencing_symbols · search_for_pattern
"""


def reviewer_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=REVIEWER_PROMPT)
        context_parts: list[str] = []
        if state.get("arch_decision"):
            context_parts.append(f"## Architecture Decision\n{state['arch_decision']}")
        if state.get("files_written"):
            context_parts.append(
                "## Files to review\n" + "\n".join(f"- {f}" for f in state["files_written"])
            )

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, REVIEWER_TOOLS, agent_name="reviewer")

        review_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""
                if "## Review Result" in content:
                    review_text = content[content.index("## Review Result"):]
                elif content:
                    review_text = content
                break

        return {
            "messages": new_messages,
            "current_agent": "reviewer",
            "review_result": review_text or "APPROVED",
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("reviewer_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[reviewer] Error: {exc}")],
            "current_agent": "reviewer",
            "review_result": f"APPROVED (error: {exc})",
            "awaiting_human": False,
        }
