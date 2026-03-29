# ── supervisor.py — Supervisor node: deterministic state-based routing ────

from __future__ import annotations

import logging

from Agents.team_agent.state import AgentState
from agent_trace import get_builder as get_tracer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def supervisor_node(state: AgentState) -> dict:
    """Route to the next agent based on state fields — no LLM call needed."""

    plan         = state.get("plan")
    arch         = state.get("arch_decision")
    review       = state.get("review_result")
    test_result  = state.get("test_result")
    files        = state.get("files_written") or []
    # Only count actual code files, not architecture docs written by the architect
    code_files   = [f for f in files if not f.endswith(".md")]
    writeup_done  = state.get("writeup_done") or False
    dev_attempts  = state.get("dev_attempts") or 0
    debug_attempts = state.get("debug_attempts") or 0

    logger.info("Supervisor state — plan=%r arch=%r files=%r code_files=%r test=%r review=%r writeup=%r dev_attempts=%s debug_attempts=%s",
                bool(plan), bool(arch), len(files), len(code_files), test_result, bool(review), writeup_done, dev_attempts, debug_attempts)

    if plan is None:
        next_agent = "planner"
        reason     = "no plan yet"
    elif arch is None:
        next_agent = "architect"
        reason     = "plan exists, no architecture decision yet"
    elif len(code_files) == 0 and (dev_attempts or 0) >= 3:
        next_agent = "END"
        reason     = "dev failed 3 times without writing code files — aborting"
    elif len(code_files) == 0:
        next_agent = "dev"
        reason     = f"architecture ready, no code written yet (attempt {(dev_attempts or 0) + 1})"
    elif test_result is None:
        next_agent = "test"
        reason     = "code written, not tested yet"
    elif "FAIL" in (test_result or "").upper() and debug_attempts >= 3:
        next_agent = "END"
        reason     = "debug failed 3 times without fixing tests — aborting"
    elif "FAIL" in (test_result or "").upper():
        next_agent = "debug"
        reason     = f"tests failed (debug attempt {debug_attempts + 1})"
    elif review is None:
        next_agent = "reviewer"
        reason     = "tests pass, no review yet"
    elif "CHANGES" in (review or "").upper():
        next_agent = "dev"
        reason     = "reviewer requested changes"
    elif not writeup_done:
        next_agent = "writeup"
        reason     = "review approved, documentation needed"
    else:
        next_agent = "END"
        reason     = "all steps complete"

    logger.info("Supervisor → %s (%s)", next_agent, reason)

    try:
        get_tracer().supervisor_route(next_agent)
    except Exception:
        pass

    return {
        "next":          next_agent,
        "current_agent": "supervisor",
        "awaiting_human": False,
    }


# ---------------------------------------------------------------------------
# Routing function used by StateGraph.add_conditional_edges
# ---------------------------------------------------------------------------

def route(state: AgentState) -> str:
    return state.get("next", "END")
