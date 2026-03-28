# ── tracer.py — Trace collector + Mermaid sequence diagram generator ────
#
# Usage:
#   from Graph.team_agent.tracer import Tracer
#   t = Tracer()
#   t.llm_call("dev", "qwen-3-235b", prompt_tokens=120, completion_tokens=340)
#   t.tool_call("dev", "write_file", {"path": "app.py"})
#   t.tool_result("dev", "write_file", "ok")
#   t.memory_op("dev", "remember", "L2+L3", "saved context")
#   print(t.to_mermaid())
#   t.save_md("/workspace/trace.md", task="Build a REST API")

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# ── Event types ───────────────────────────────────────────────────────────────

EventType = Literal[
    "agent_start",
    "llm_call",
    "llm_response",
    "tool_call",
    "tool_result",
    "memory_op",
    "supervisor_route",
    "agent_done",
    "error",
]

_AGENT_ICONS: dict[str, str] = {
    "planner":    "📋 Planner",
    "architect":  "🏗️ Architect",
    "dev":        "💻 Developer",
    "test":       "🧪 Tester",
    "debug":      "🐛 Debugger",
    "reviewer":   "🔍 Reviewer",
    "writeup":    "📝 Writeup",
    "analyst":    "📊 Analyst",
    "supervisor": "🎯 Supervisor",
    "user":       "👤 User",
    "llm":        "🤖 LLM",
    "memory":     "🧠 Memory",
    "filesystem": "💾 Filesystem",
}

_DB_ICONS: dict[str, str] = {
    "L2": "🔴 Redis (L2)",
    "L3": "🟠 ChromaDB (L3)",
    "L4": "🟣 Postgres (L4)",
}


@dataclass
class TraceEvent:
    ts: str                          # ISO timestamp
    event_type: EventType
    agent: str                       # emitting agent name
    payload: dict                    # event-specific data


# ── Tracer ────────────────────────────────────────────────────────────────────

class Tracer:
    """Accumulates trace events and renders them as a Mermaid sequence diagram."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []
        self._started_at: str = _now()

    # ── Public event recorders ────────────────────────────────────────────────

    def agent_start(self, agent: str) -> None:
        self._add("agent_start", agent, {})

    def agent_done(self, agent: str, duration_ms: int) -> None:
        self._add("agent_done", agent, {"duration_ms": duration_ms})

    def supervisor_route(self, target: str) -> None:
        self._add("supervisor_route", "supervisor", {"target": target})

    def llm_call(
        self,
        agent: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        iteration: int = 1,
    ) -> None:
        self._add("llm_call", agent, {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "iteration": iteration,
        })

    def tool_call(self, agent: str, tool_name: str, args: dict) -> None:
        # Summarise args for display — avoid giant payloads
        summary = _summarise_args(tool_name, args)
        self._add("tool_call", agent, {"tool": tool_name, "args_summary": summary})

    def tool_result(self, agent: str, tool_name: str, result: str) -> None:
        short = result[:120].replace("\n", " ") + ("…" if len(result) > 120 else "")
        self._add("tool_result", agent, {"tool": tool_name, "result": short})

    def memory_op(
        self,
        agent: str,
        operation: Literal["remember", "recall", "commit_to_identity", "inject"],
        layer: str,
        summary: str,
    ) -> None:
        self._add("memory_op", agent, {
            "operation": operation,
            "layer": layer,
            "summary": summary[:120],
        })

    def error(self, agent: str, message: str) -> None:
        self._add("error", agent, {"message": message[:200]})

    # ── Mermaid generation ────────────────────────────────────────────────────

    def to_mermaid(self) -> str:
        """Return the full Mermaid sequenceDiagram string."""
        lines: list[str] = ["sequenceDiagram"]
        lines.append("    autonumber")
        lines.append("")

        # Participants — declare in order of first appearance
        seen_participants: list[str] = []
        participants = _collect_participants(self.events)
        for p in participants:
            label = _AGENT_ICONS.get(p, p)
            lines.append(f"    participant {p} as {label}")
            seen_participants.append(p)
        lines.append("")

        # Events → sequence arrows
        for ev in self.events:
            lines.extend(_render_event(ev))

        return "\n".join(lines)

    def to_mermaid_block(self) -> str:
        """Wrapped in a ```mermaid fence for Markdown embedding."""
        return "```mermaid\n" + self.to_mermaid() + "\n```"

    # ── Markdown export ───────────────────────────────────────────────────────

    def to_markdown(self, task: str = "") -> str:
        """Full trace report as Markdown (diagram + stats table + event log)."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        sections: list[str] = []

        # Header
        sections.append(f"# Agent Trace Report\n")
        sections.append(f"**Task:** {task or '(unknown)'}")
        sections.append(f"**Started:** {self._started_at}")
        sections.append(f"**Generated:** {now}")
        sections.append(f"**Total events:** {len(self.events)}\n")

        # Stats
        sections.append("## Token Usage by Agent\n")
        sections.append(_render_token_table(self.events))

        # Memory ops summary
        sections.append("\n## Memory Operations\n")
        sections.append(_render_memory_table(self.events))

        # Diagram
        sections.append("\n## Sequence Diagram\n")
        sections.append(self.to_mermaid_block())

        # Full event log
        sections.append("\n## Full Event Log\n")
        sections.append("| # | Time | Agent | Event | Detail |")
        sections.append("|---|------|-------|-------|--------|")
        for i, ev in enumerate(self.events, 1):
            detail = _event_detail(ev)
            sections.append(
                f"| {i} | `{ev.ts}` | `{ev.agent}` | `{ev.event_type}` | {detail} |"
            )

        return "\n".join(sections)

    def save_md(self, path: str | Path, task: str = "") -> Path:
        """Write the trace report to a Markdown file. Returns the resolved path."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        content = self.to_markdown(task=task)
        p.write_text(content, encoding="utf-8")
        return p

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _add(self, event_type: EventType, agent: str, payload: dict) -> None:
        self.events.append(TraceEvent(ts=_now(), event_type=event_type, agent=agent, payload=payload))


# ── Module-level singleton (shared across tool_loop calls in one session) ─────

_active_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Return the module-level active tracer, creating one if needed."""
    global _active_tracer
    if _active_tracer is None:
        _active_tracer = Tracer()
    return _active_tracer


def reset_tracer() -> Tracer:
    """Reset and return a fresh tracer (call at the start of each new task)."""
    global _active_tracer
    _active_tracer = Tracer()
    return _active_tracer


# ── Private helpers ───────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _summarise_args(tool_name: str, args: dict) -> str:
    """Return a short human-readable summary of tool arguments."""
    if tool_name == "write_file":
        path = args.get("path", "?")
        content = args.get("content", "")
        lines = content.count("\n") + 1 if content else 0
        return f"path={path}  ({lines} lines)"
    if tool_name == "read_file":
        return f"path={args.get('path', '?')}"
    if tool_name == "run_shell":
        cmd = str(args.get("command", "?"))
        return cmd[:80] + ("…" if len(cmd) > 80 else "")
    if tool_name in ("remember", "recall", "commit_to_identity"):
        content = str(args.get("content", args.get("query", "?")))
        return content[:80] + ("…" if len(content) > 80 else "")
    if tool_name in ("git_commit",):
        return f"message={args.get('message', '?')[:60]}"
    # Generic fallback
    parts = [f"{k}={str(v)[:40]}" for k, v in list(args.items())[:3]]
    return "  ".join(parts) or "(no args)"


def _collect_participants(events: list[TraceEvent]) -> list[str]:
    """Collect participants in appearance order, always include standard ones."""
    order = ["user"]
    seen = {"user"}

    # Always include memory and filesystem if used
    for ev in events:
        if ev.agent not in seen:
            order.append(ev.agent)
            seen.add(ev.agent)
        if ev.event_type == "tool_call":
            tool = ev.payload.get("tool", "")
            if tool in ("write_file", "read_file", "git_commit", "git_diff") and "filesystem" not in seen:
                order.append("filesystem")
                seen.add("filesystem")
            if tool in ("remember", "recall", "commit_to_identity") and "memory" not in seen:
                order.append("memory")
                seen.add("memory")
        if ev.event_type in ("llm_call", "llm_response") and "llm" not in seen:
            # Insert llm after the agent if not already present
            idx = order.index(ev.agent) + 1 if ev.agent in order else len(order)
            order.insert(idx, "llm")
            seen.add("llm")

    return order


def _render_event(ev: TraceEvent) -> list[str]:
    """Convert one TraceEvent to one or more Mermaid sequence diagram lines."""
    p = ev.payload
    lines: list[str] = []

    if ev.event_type == "agent_start":
        lines.append(f"    Note over {ev.agent}: ▶ start")

    elif ev.event_type == "agent_done":
        ms = p.get("duration_ms", 0)
        lines.append(f"    Note over {ev.agent}: ◀ done ({ms}ms)")

    elif ev.event_type == "supervisor_route":
        target = p.get("target", "?")
        lines.append(f"    supervisor->>{target}: route → {target}")

    elif ev.event_type == "llm_call":
        model = p.get("model", "?")
        prompt = p.get("prompt_tokens", 0)
        completion = p.get("completion_tokens", 0)
        total = p.get("total_tokens", 0)
        it = p.get("iteration", 1)
        lines.append(f"    {ev.agent}->>llm: [{model}] iter={it}")
        if total > 0:
            lines.append(f"    Note right of llm: prompt={prompt} · completion={completion} · total={total}")

    elif ev.event_type == "llm_response":
        has_tools = p.get("has_tool_calls", False)
        suffix = " (+ tool_calls)" if has_tools else ""
        lines.append(f"    llm-->>{ev.agent}: response{suffix}")

    elif ev.event_type == "tool_call":
        tool = p.get("tool", "?")
        summary = p.get("args_summary", "")
        target = _tool_target(tool)
        lines.append(f"    {ev.agent}->>{target}: {tool}({summary})")

    elif ev.event_type == "tool_result":
        tool = p.get("tool", "?")
        result = p.get("result", "")
        target = _tool_target(tool)
        lines.append(f"    {target}-->>{ev.agent}: ✓ {result}")

    elif ev.event_type == "memory_op":
        op = p.get("operation", "?")
        layer = p.get("layer", "?")
        summary = p.get("summary", "")
        db_label = _DB_ICONS.get(layer, layer)
        arrow = "->>" if op in ("remember", "commit_to_identity") else "-->>"
        if op in ("remember", "commit_to_identity"):
            lines.append(f"    {ev.agent}->>memory: {op} [{layer}]")
            lines.append(f"    Note right of memory: {summary}")
        else:  # recall / inject
            lines.append(f"    memory-->>{ev.agent}: {op} [{layer}] {summary}")

    elif ev.event_type == "error":
        msg = p.get("message", "")
        lines.append(f"    Note over {ev.agent}: ❌ ERROR: {msg}")

    return lines


def _tool_target(tool_name: str) -> str:
    """Map tool name to its participant."""
    if tool_name in ("write_file", "read_file", "git_commit", "git_diff"):
        return "filesystem"
    if tool_name in ("remember", "recall", "commit_to_identity"):
        return "memory"
    return "filesystem"  # run_shell and others → filesystem


def _render_token_table(events: list[TraceEvent]) -> str:
    """Markdown table of token usage aggregated per agent."""
    usage: dict[str, dict] = {}
    for ev in events:
        if ev.event_type == "llm_call":
            p = ev.payload
            a = ev.agent
            if a not in usage:
                usage[a] = {"model": p.get("model", "?"), "calls": 0, "prompt": 0, "completion": 0, "total": 0}
            usage[a]["calls"] += 1
            usage[a]["prompt"]     += p.get("prompt_tokens", 0)
            usage[a]["completion"] += p.get("completion_tokens", 0)
            usage[a]["total"]      += p.get("total_tokens", 0)

    if not usage:
        return "_No LLM calls recorded._"

    rows = ["| Agent | Model | Calls | Prompt | Completion | Total |",
            "|-------|-------|-------|--------|------------|-------|"]
    for agent, u in usage.items():
        rows.append(
            f"| `{agent}` | `{u['model']}` | {u['calls']} "
            f"| {u['prompt']:,} | {u['completion']:,} | **{u['total']:,}** |"
        )
    # Grand total row
    grand_prompt = sum(u["prompt"] for u in usage.values())
    grand_comp   = sum(u["completion"] for u in usage.values())
    grand_total  = sum(u["total"] for u in usage.values())
    rows.append(f"| **TOTAL** | | | {grand_prompt:,} | {grand_comp:,} | **{grand_total:,}** |")
    return "\n".join(rows)


def _render_memory_table(events: list[TraceEvent]) -> str:
    """Markdown table of all memory operations."""
    ops = [ev for ev in events if ev.event_type == "memory_op"]
    if not ops:
        return "_No memory operations recorded._"

    rows = ["| Agent | Operation | Layer | Summary |",
            "|-------|-----------|-------|---------|"]
    for ev in ops:
        p = ev.payload
        rows.append(
            f"| `{ev.agent}` | `{p.get('operation','?')}` "
            f"| `{p.get('layer','?')}` | {p.get('summary','')} |"
        )
    return "\n".join(rows)


def _event_detail(ev: TraceEvent) -> str:
    """One-line detail string for the event log table."""
    p = ev.payload
    if ev.event_type == "llm_call":
        return f"model=`{p.get('model','?')}` prompt={p.get('prompt_tokens',0)} comp={p.get('completion_tokens',0)} total={p.get('total_tokens',0)}"
    if ev.event_type == "tool_call":
        return f"`{p.get('tool','?')}` — {p.get('args_summary','')}"
    if ev.event_type == "tool_result":
        return f"`{p.get('tool','?')}` → {p.get('result','')}"
    if ev.event_type == "memory_op":
        return f"`{p.get('operation','?')}` [{p.get('layer','?')}] {p.get('summary','')}"
    if ev.event_type == "supervisor_route":
        return f"→ `{p.get('target','?')}`"
    if ev.event_type == "error":
        return p.get("message", "")
    if ev.event_type == "agent_done":
        return f"{p.get('duration_ms',0)}ms"
    return ""
