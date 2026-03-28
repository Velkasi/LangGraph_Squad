# ── architect.py — Architect agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import SIMPLE_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import write_file
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

ARCHITECT_TOOLS = [write_file]  # uniquement write_file pour DESIGN.md

ARCHITECT_PROMPT = """You are the **Architect** in an AI software-development team.

## ## Role
Define the technical architecture for the project.

## Responsibilities
- Choose the technology stack.
- Define system structure and module boundaries.
- Specify data flows and APIs between modules.
- Produce a concise architecture document.

## Task
Create an architecture document and save it as `DESIGN.md` using `write_file`.

## Output Rules
- Write the architecture document content to `DESIGN.md`.
- Be concise and structured.
- Do not include explanations outside the document.

## Required Final Section
End the document with:

## Architecture Decision
**Stack:** ...
**Structure:** ...
**Key decisions:** ...

## Tools
write_file
"""


def architect_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=ARCHITECT_PROMPT)
        context_parts: list[str] = []
        if state.get("plan"):
            context_parts.append(f"## Plan\n{state['plan']}")

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, ARCHITECT_TOOLS, agent_name="architect")

        arch_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""
                if "## Architecture Decision" in content:
                    arch_text = content[content.index("## Architecture Decision"):]
                elif content:
                    arch_text = content
                break

        decision = arch_text or "(architecture defined)"
        logger.info("architect_node done — arch_decision=%r", decision[:60])
        return {
            "messages": new_messages,
            "current_agent": "architect",
            "arch_decision": decision,
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("architect_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[architect] Error: {exc}")],
            "current_agent": "architect",
            "arch_decision": f"(error: {exc})",
            "awaiting_human": False,
        }
