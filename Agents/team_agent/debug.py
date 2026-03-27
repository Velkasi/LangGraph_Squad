# ── debug.py — Debug agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import MEDIUM_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file
from Tools.team_agent.memory_tools import recall, remember
from Tools.team_agent.shell_tools import run_shell
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

DEBUG_TOOLS = [read_file, run_shell, remember, recall]

DEBUG_PROMPT = """You are the **Debugger** in an AI software-development team.

## Your responsibilities
- Investigate test failures and runtime errors reported by the test agent.
- Use `read_file` to inspect failing code and log files.
- Use `run_shell` to run targeted diagnostics.
- Identify the root cause and describe the exact fix needed.
- Use `remember` to log the bug and root cause for future reference.

## Output format
```
## Debug Report
**Root cause:** ...
**Affected file(s):** ...
**Fix:** ...
```

## Rules
- Do NOT write code fixes — describe the fix and let the dev agent apply it.

## Available tools
read_file · run_shell · remember · recall
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

        new_messages, _ = run_tool_loop(MODEL, MODEL_PROVIDER, messages, DEBUG_TOOLS)

        return {
            "messages": new_messages,
            "current_agent": "debug",
            "test_result": None,
            "awaiting_human": False,
        }
    except Exception as exc:
        logger.warning("debug_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[debug] Error: {exc}")], "current_agent": "debug", "test_result": None, "awaiting_human": False}
