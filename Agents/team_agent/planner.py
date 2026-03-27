# ── planner.py — Planner agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import COMPLEX_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.memory_tools import commit_to_identity, remember, recall
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

PLANNER_TOOLS = [remember, recall, commit_to_identity]

PLANNER_PROMPT = """You are the **Planner** in an AI software-development team.

## Your responsibilities
- Analyse the user's task and produce a clear, numbered, step-by-step plan.
- Identify required inputs, dependencies, and success criteria for each step.
- Use `recall` to retrieve relevant prior context before planning.
- Use `remember` to persist key planning decisions.
- Assign each step to the most appropriate agent:
  architect · dev · reviewer · debug · test · writeup · analyst

## Output format
Always end your response with a Markdown section:
```
## Plan
1. [agent] Description of step
2. [agent] Description of step
...
```

## Available tools
remember · recall · commit_to_identity
"""


def planner_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=PLANNER_PROMPT)
        task_hint = SystemMessage(content=f"## Task\n{state.get('task', '(no task set)')}")

        new_messages, _ = run_tool_loop(
            MODEL, MODEL_PROVIDER,
            [system, task_hint] + state["messages"],
            PLANNER_TOOLS,
        )

        plan_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""
                if "## Plan" in content:
                    plan_text = content[content.index("## Plan"):]
                elif content:
                    plan_text = content
                break

        return {
            "messages": new_messages,
            "current_agent": "planner",
            "plan": plan_text or "",
            "awaiting_human": False,
        }
    except Exception as exc:
        logger.warning("planner_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[planner] Error: {exc}")], "current_agent": "planner", "awaiting_human": False}
