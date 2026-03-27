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

## Your responsibilities
- Make high-level technology, structure, and design decisions based on the plan.
- Define module boundaries, data flows, APIs, and technology choices.
- Use `write_file` to save a `DESIGN.md` architecture document in the workspace.

## Output format
Always end your response with a Markdown section:
```
## Architecture Decision
**Stack:** ...
**Structure:** ...
**Key decisions:** ...
```

## Available tools
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

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, ARCHITECT_TOOLS)

        arch_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""
                if "## Architecture Decision" in content:
                    arch_text = content[content.index("## Architecture Decision"):]
                elif content:
                    arch_text = content
                break

        return {
            "messages": new_messages,
            "current_agent": "architect",
            "arch_decision": arch_text or "",
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("architect_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[architect] Error: {exc}")], "current_agent": "architect", "awaiting_human": False}
