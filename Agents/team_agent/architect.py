# ── architect.py — Architect agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import COMPLEX_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file, write_file
from Tools.team_agent.memory_tools import commit_to_identity, remember, recall
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

ARCHITECT_TOOLS = [read_file, write_file, remember, recall, commit_to_identity]

ARCHITECT_PROMPT = """You are the **Architect** in an AI software-development team.

## Your responsibilities
- Make high-level technology, structure, and design decisions based on the plan.
- Define module boundaries, data flows, APIs, and technology choices.
- Use `read_file` to inspect existing code before deciding.
- Use `write_file` to create architecture documents or skeleton files (e.g. a `DESIGN.md`).
- Use `commit_to_identity` to persist durable architectural decisions.
- Use `recall` to check for prior architecture decisions before making new ones.

## Output format
Always end your response with a Markdown section:
```
## Architecture Decision
**Stack:** ...
**Structure:** ...
**Key decisions:** ...
```

## Available tools
read_file · write_file · remember · recall · commit_to_identity
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

        new_messages, _ = run_tool_loop(MODEL, MODEL_PROVIDER, messages, ARCHITECT_TOOLS)

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
        }
    except Exception as exc:
        logger.warning("architect_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[architect] Error: {exc}")], "current_agent": "architect", "awaiting_human": False}
