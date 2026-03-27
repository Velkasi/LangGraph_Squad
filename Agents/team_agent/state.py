# ── state.py — Shared AgentState TypedDict for the team_agent graph ────

from __future__ import annotations

from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state passed between every node in the team_agent graph."""

    # Conversation history — append-only via add_messages reducer
    messages: Annotated[list, add_messages]

    # High-level task description set by the user at graph entry
    task: str

    # Name of the agent that last wrote to this state
    current_agent: str

    # Paths of every file written during the current run
    files_written: list[str]

    # When True the graph pauses and waits for human approval
    awaiting_human: bool

    # Routing decision set by the supervisor
    next: str

    # Structured outputs produced by specific agents
    plan: Optional[str]           # set by planner
    arch_decision: Optional[str]  # set by architect
    review_result: Optional[str]  # set by reviewer
    test_result: Optional[str]    # set by test agent
    writeup_done: Optional[bool]  # set by writeup agent
    dev_attempts: Optional[int]   # nombre de passages dans dev sans écriture
