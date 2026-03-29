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

## Permissions
ALLOWED:
- Analyze the user request
- Produce a step-by-step plan
- Assign steps to agents: architect · dev · reviewer · debug · test · writeup · analyst

FORBIDDEN:
- Calling any tool (you have none)
- Writing or reading files
- Making architecture decisions
- Writing code, configuration, or documentation
- Invoking any other agent directly

## Step Content
Each step must include:
- objective
- required inputs (if any)
- success criteria

## Output
End your response with TWO sections in this EXACT order:

## Files
List EVERY file path the dev must produce, one per line, relative paths only.
Example:
src/main.py
src/utils.py
requirements.txt
docker-compose.yml
.env.example

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
        files_target: list[str] = []

        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else ""
                if not content.strip():
                    continue
                if "## Plan" in content:
                    plan_text = content[content.index("## Plan"):]
                elif content:
                    plan_text = content

                # Extract ## Files section → files_target
                if "## Files" in content:
                    files_block = content[content.index("## Files"):].split("## Plan")[0]
                    for line in files_block.splitlines():
                        line = line.strip()
                        # Strip list markers: "- ", "* ", "1. ", "10. ", etc.
                        import re as _re
                        line = _re.sub(r"^[-*]\s+", "", line)
                        line = _re.sub(r"^\d+\.\s+", "", line)
                        line = line.strip()
                        # Accept only lines that look like a file path (has extension or is a known file)
                        if line and not line.startswith("#") and ("." in line or line in ("Makefile", "Dockerfile")):
                            # Remove trailing comments (e.g. "src/main.py  # entry point")
                            line = line.split("#")[0].split("  ")[0].strip()
                            if line:
                                files_target.append(line)
                break

        plan = plan_text or "(plan defined)"
        logger.info("planner_node done — plan=%r files_target=%r", plan[:60], files_target)
        return {
            "messages": new_messages,
            "current_agent": "planner",
            "plan": plan,
            "files_target": files_target or None,
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("planner_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[planner] Error: {exc}")],
            "current_agent": "planner",
            "plan": f"(error: {exc})",
            "awaiting_human": False,
        }
