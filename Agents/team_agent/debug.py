# ── debug.py — Debug agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import MEDIUM_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file
from Tools.team_agent.memory_tools import recall, remember
from Tools.team_agent.serena_tools import get_serena_tools
from Tools.team_agent.shell_tools import run_shell
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

DEBUG_TOOLS = [
    read_file, run_shell, remember, recall,
    *get_serena_tools(),
]

DEBUG_PROMPT = """You are the Debugger in an AI software team.

## Permissions
ALLOWED:
- Read files with `read_file`
- Run read-only diagnostics with `run_shell` (logs, ps, env, curl checks)
- Inspect symbols with `find_symbol`, `find_referencing_symbols`, `search_for_pattern`
- Store non-obvious root cause patterns with `remember`
- Retrieve prior constraints with `recall`

FORBIDDEN:
- Modifying or creating any file
- Running destructive shell commands (rm, DROP, reset, kill -9, etc.)
- Implementing fixes (describe them precisely; dev implements)
- Committing code

## Task
Investigate test failures or runtime errors and determine the root cause.

Do not modify code. Only diagnose and describe the fix.

## Process
1. Inspect failing files and logs using `read_file`.
2. Run targeted diagnostics using `run_shell`.
3. Locate the failing symbol using `find_symbol`.
4. Trace all usages with `find_referencing_symbols`.
5. Use `search_for_pattern` to locate similar issues across files.
6. Identify the root cause and the exact fix required.
7. Record the root cause using `remember` ONLY if it reveals a non-obvious constraint (e.g. "Library X silently swallows errors in async context").

## Output

## Debug Report
**Root cause:** ...
**Affected file(s):** ...
**Fix:** ...

## Rules
- Do not write code.
- Provide the precise fix so the Developer agent can implement it.

## Memory rules (STRICT)
Use `remember` ONLY for:
- A non-obvious constraint or root cause pattern (e.g. "Library X swallows async errors silently")
- A systemic bug pattern that may recur in future agents

NEVER use `remember` for:
- Bug descriptions already visible in the test_result
- Status updates ("Debug complete", "Root cause found")

Use `recall` at the start to retrieve known constraints before debugging.

## Tools
read_file · run_shell · remember · recall
find_symbol · find_referencing_symbols · search_for_pattern
"""


def debug_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=DEBUG_PROMPT)
        context_parts: list[str] = []
        if state.get("test_result"):
            context_parts.append(f"## Test result (failure)\n{state['test_result']}")

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, DEBUG_TOOLS, agent_name="debug")

        return {
            "messages": new_messages,
            "current_agent": "debug",
            "test_result": None,   # reset so supervisor sends back to test after debug
            "debug_attempts": (state.get("debug_attempts") or 0) + 1,
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("debug_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[debug] Error: {exc}")],
            "current_agent": "debug",
            "test_result": None,
            "debug_attempts": (state.get("debug_attempts") or 0) + 1,
            "awaiting_human": False,
        }
