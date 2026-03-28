# ── planner.py — Planner agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import SIMPLE_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

PLANNER_TOOLS = []  # pas de tools — une seule invocation LLM, zéro re-invocation

PLANNER_PROMPT = """You are the Planner in an AI software team.

## Task
Analyze the user's request and produce a clear execution plan.

## Rules
- Break the work into ordered steps.
- Each step must be assigned to one agent:
  architect · dev · reviewer · debug · test · writeup · analyst
- Steps must be actionable and concise.
- Do not implement anything.

## Step Content
Each step must include:
- objective
- required inputs (if any)
- success criteria

## Output
End your response with:

## Plan
1. [agent] Objective — inputs — success criteria
2. [agent] Objective — inputs — success criteria
...
"""


def planner_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=PLANNER_PROMPT)
        task_hint = SystemMessage(content=f"## Task\n{state.get('task', '(no task set)')}")

        new_messages, _, tokens = run_tool_loop(
            MODEL, MODEL_PROVIDER,
            [system, task_hint] + state["messages"],
            PLANNER_TOOLS,
            agent_name="planner",
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
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("planner_node failed: %s", exc)
        return {"messages": [AIMessage(content=f"[planner] Error: {exc}")], "current_agent": "planner", "awaiting_human": False}
