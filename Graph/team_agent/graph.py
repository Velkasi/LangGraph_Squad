# ── graph.py — StateGraph definition: nodes, edges, checkpointer, compilation ────

from __future__ import annotations

import logging
import time

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("team_agent")


def _timed_node(name: str, fn):
    """Wrap a node function to log start, end, and elapsed time."""
    def wrapper(state):
        _log.info("▶  %-12s  starting…", name)
        t0 = time.perf_counter()
        result = fn(state)
        elapsed = time.perf_counter() - t0
        _log.info("◀  %-12s  done  (%.2fs)", name, elapsed)
        return result
    wrapper.__name__ = fn.__name__
    return wrapper

from Agents.team_agent.analyst import analyst_node
from Agents.team_agent.architect import architect_node
from Agents.team_agent.debug import debug_node
from Agents.team_agent.dev import dev_node
from Agents.team_agent.planner import planner_node
from Agents.team_agent.reviewer import reviewer_node
from Agents.team_agent.state import AgentState
from Agents.team_agent.supervisor import route, supervisor_node
from Agents.team_agent.test import test_node
from Agents.team_agent.writeup import writeup_node
from Config.team_agent.config import INTERRUPT_BEFORE

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

builder = StateGraph(AgentState)

# ── Nodes ─────────────────────────────────────────────────────────────────────
builder.add_node("supervisor", _timed_node("supervisor", supervisor_node))
builder.add_node("planner",    _timed_node("planner",    planner_node))
builder.add_node("architect",  _timed_node("architect",  architect_node))
builder.add_node("dev",        _timed_node("dev",        dev_node))
builder.add_node("reviewer",   _timed_node("reviewer",   reviewer_node))
builder.add_node("debug",      _timed_node("debug",      debug_node))
builder.add_node("test",       _timed_node("test",       test_node))
builder.add_node("writeup",    _timed_node("writeup",    writeup_node))
builder.add_node("analyst",    _timed_node("analyst",    analyst_node))

# ── Entry point ───────────────────────────────────────────────────────────────
builder.set_entry_point("supervisor")

# ── Conditional edges: supervisor → agents ────────────────────────────────────
builder.add_conditional_edges(
    "supervisor",
    route,
    {
        "planner":   "planner",
        "architect": "architect",
        "dev":       "dev",
        "reviewer":  "reviewer",
        "debug":     "debug",
        "test":      "test",
        "writeup":   "writeup",
        "analyst":   "analyst",
        "END":       END,
    },
)

# ── Each agent loops back to the supervisor ───────────────────────────────────
for _agent in ["planner", "architect", "dev", "reviewer", "debug", "test", "writeup", "analyst"]:
    builder.add_edge(_agent, "supervisor")

# ── Compile with checkpointer and human-in-the-loop interrupts ───────────────
graph = builder.compile(
    checkpointer=MemorySaver(),
    interrupt_before=INTERRUPT_BEFORE,  # ["dev", "architect"] from config
)

__all__ = ["graph"]
