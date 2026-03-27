# ── writeup.py — Writeup agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import SIMPLE_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file, write_file
from Tools.team_agent.memory_tools import recall, remember
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

WRITEUP_TOOLS = [read_file, write_file, remember, recall]

WRITEUP_PROMPT = """You are the **Technical Writer** in an AI software-development team.

## Your responsibilities
- Read source files using `read_file` to understand what was built.
- Use `recall` to retrieve the plan, architecture decision, and review result.
- Produce clear, accurate documentation: README.md, CHANGELOG.md.
- Write documentation files using `write_file`.
- Use `remember` to log that documentation was updated.

## Rules
- Write in plain English.
- Do not document code that was not produced in this session.

## Available tools
read_file · write_file · remember · recall
"""


def writeup_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=WRITEUP_PROMPT)
        context_parts: list[str] = []
        if state.get("plan"):
            context_parts.append(f"## Plan\n{state['plan']}")
        if state.get("files_written"):
            context_parts.append(
                "## Files written\n" + "\n".join(f"- {f}" for f in state["files_written"])
            )

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _ = run_tool_loop(MODEL, MODEL_PROVIDER, messages, WRITEUP_TOOLS)

        return {
            "messages": new_messages,
            "current_agent": "writeup",
            "writeup_done": True,
            "awaiting_human": False,
        }
    except Exception as exc:
        logger.warning("writeup_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[writeup] Error: {exc}")], "current_agent": "writeup", "writeup_done": True, "awaiting_human": False}
