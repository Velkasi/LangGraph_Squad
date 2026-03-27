# ── analyst.py — Analyst agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import SIMPLE_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file, write_file
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

ANALYST_TOOLS = [read_file, write_file]

ANALYST_PROMPT = """You are the **Analyst** in an AI software-development team.

## Your responsibilities
- Analyse requirements, specifications, or data files provided by the user.
- Identify ambiguities, contradictions, or missing requirements.
- Use `read_file` to load data files or specification documents.
- Use `write_file` to save analysis reports (e.g. `REQUIREMENTS.md`, `ANALYSIS.md`).

## Output format
```
## Analysis Report
**Summary:** ...
**Key requirements:** ...
**Ambiguities / risks:** ...
**Acceptance criteria:** ...
```

## Available tools
read_file · write_file
"""


def analyst_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=ANALYST_PROMPT)
        task_hint = SystemMessage(content=f"## Task\n{state.get('task', '(no task set)')}")

        new_messages, _, tokens = run_tool_loop(
            MODEL, MODEL_PROVIDER,
            [system, task_hint] + state["messages"],
            ANALYST_TOOLS,
        )

        return {
            "messages": new_messages,
            "current_agent": "analyst",
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("analyst_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[analyst] Error: {exc}")], "current_agent": "analyst", "awaiting_human": False}
