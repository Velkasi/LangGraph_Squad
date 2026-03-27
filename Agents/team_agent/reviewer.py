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

REVIEWER_PROMPT = """You are the **Reviewer** in an AI software-development team. You are strict and thorough.

## Your responsibilities
- Use `read_file` to read EVERY file listed in `files_written` — do not skip any.
- Cross-check all imports: every `import` or `require` must resolve to a file that exists in `files_written` or is a known npm/pip package.
- Verify package names are correct (e.g. `@supabase/supabase-js` not `supabase-js`).
- Check Docker images actually exist on Docker Hub (e.g. `supabase/supabase:latest` does NOT exist).
- Check that every file referenced in `docker-compose.yml` (Dockerfiles, volumes, configs) exists in `files_written`.
- Flag any environment variable used in code that is not declared in `docker-compose.yml` or a `.env.example`.
- Use `find_symbol` to confirm every imported symbol actually exists in its source file.
- Use `find_referencing_symbols` to check nothing is calling a symbol that was removed.
- Use `search_for_pattern` to scan for hardcoded secrets or forbidden patterns across all files.
- Check for hardcoded secrets, missing error handling, and unhandled promise rejections.

## Mandatory checks (BLOCKING if failed)
1. Every import resolves to an existing file or valid package
2. All Dockerfiles referenced in docker-compose exist
3. No invalid/non-existent Docker images
4. No hardcoded secrets in committed files
5. No missing files that code depends on

## Output format
Always end your response with:
```
## Review Result
**Status:** APPROVED | CHANGES_REQUESTED
**Blocking issues:**
- ...
**Warnings:**
- ...
```

Only set **Status: APPROVED** if there are zero blocking issues.

## Available tools
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

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, REVIEWER_TOOLS)

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
            "review_result": review_text or "",
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("reviewer_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[reviewer] Error: {exc}")], "current_agent": "reviewer", "awaiting_human": False}
