# ── app.py — Streamlit interface: chat UI with real-time trace ────

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import uuid
import time

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from Graph.team_agent.graph import graph

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Team Agent",
    page_icon="🤖",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []  # list[dict] with keys "role" and "content"

if "graph_config" not in st.session_state:
    st.session_state.graph_config = {
        "configurable": {"thread_id": st.session_state.thread_id}
    }

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Team Agent")
    st.caption("AI software-development team powered by LangGraph")
    st.divider()

    st.subheader("Session")
    st.code(st.session_state.thread_id, language=None)

    if st.button("New session", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.graph_config = {
            "configurable": {"thread_id": st.session_state.thread_id}
        }
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Graph state")
    try:
        snapshot = graph.get_state(st.session_state.graph_config)
        values = snapshot.values if snapshot else {}
        st.write("Current agent:", values.get("current_agent", "—"))
        st.write("Files written:", len(values.get("files_written") or []))
        next_nodes = snapshot.next if snapshot else []
        if next_nodes:
            st.write("Next node:", ", ".join(next_nodes))
    except Exception:
        st.write("(no active state)")

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

st.title("Team Agent")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

prompt = st.chat_input("Describe the task for the team…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── Real-time trace panel ──────────────────────────────────────────────
    _AGENT_ICONS = {
        "planner":    "📋",
        "architect":  "🏗️",
        "dev":        "💻",
        "test":       "🧪",
        "debug":      "🐛",
        "reviewer":   "🔍",
        "writeup":    "📝",
        "analyst":    "📊",
        "supervisor": "🎯",
    }

    trace_container = st.container()
    with trace_container:
        st.divider()
        st.caption("**Live trace**")
        status_placeholder   = st.empty()   # current agent badge
        tool_placeholder     = st.empty()   # tool calls in progress
        files_placeholder    = st.empty()   # files written so far
        tokens_placeholder   = st.empty()   # token counter
        progress_placeholder = st.empty()   # step counter

    _all_files: list[str] = []
    _step = 0
    _total_tokens = {"prompt": 0, "completion": 0, "total": 0}

    def _render_trace(agent: str, tool_calls: list[str], files: list[str], step: int):
        icon = _AGENT_ICONS.get(agent, "🤖")
        status_placeholder.markdown(
            f"**{icon} Agent actif :** `{agent}`" if agent else "**En attente…**"
        )
        if tool_calls:
            lines = "\n".join(f"- `{t}`" for t in tool_calls[-5:])
            tool_placeholder.markdown(f"**Outils appelés :**\n{lines}")
        else:
            tool_placeholder.empty()

        if files:
            flines = "\n".join(f"- `{f}`" for f in files)
            files_placeholder.markdown(f"**Fichiers écrits ({len(files)}) :**\n{flines}")
        else:
            files_placeholder.empty()

        tokens_placeholder.markdown(
            f"**Tokens** — prompt: `{_total_tokens['prompt']:,}` "
            f"· completion: `{_total_tokens['completion']:,}` "
            f"· **total: `{_total_tokens['total']:,}`**"
        )
        progress_placeholder.caption(f"Étape {step}")

    try:
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "task": prompt,
            "current_agent": "",
            "files_written": [],
            "awaiting_human": False,
            "plan": None,
            "arch_decision": None,
            "review_result": None,
            "test_result": None,
            "writeup_done": False,
            "dev_attempts": 0,
                "token_usage": None,
        }

        _current_agent = ""
        _tool_calls_seen: list[str] = []

        for chunk in graph.stream(
            initial_state,
            config=st.session_state.graph_config,
        ):
            for node_name, node_output in chunk.items():
                if node_name in ("__end__", "__interrupt__"):
                    continue
                if not isinstance(node_output, dict):
                    continue

                _step += 1
                _current_agent = node_name

                # Collect tool calls from AIMessages
                msgs = node_output.get("messages", [])
                for m in msgs:
                    if isinstance(m, AIMessage):
                        for tc in getattr(m, "tool_calls", None) or []:
                            name = tc.get("name") if isinstance(tc, dict) else tc.name
                            if name and name not in _tool_calls_seen:
                                _tool_calls_seen.append(name)

                # Track files written
                new_files = node_output.get("files_written") or []
                for f in new_files:
                    if f not in _all_files:
                        _all_files.append(f)

                # Accumulate token usage
                usage = node_output.get("token_usage") or {}
                _total_tokens["prompt"]     += usage.get("prompt_tokens", 0)
                _total_tokens["completion"] += usage.get("completion_tokens", 0)
                _total_tokens["total"]      += usage.get("total_tokens", 0)

                # Update trace panel
                _render_trace(_current_agent, _tool_calls_seen, _all_files, _step)

                # Collect assistant messages for chat history
                for m in msgs:
                    content = m.content if hasattr(m, "content") else str(m)
                    if content and not isinstance(m, ToolMessage):
                        st.session_state.messages.append(
                            {"role": "assistant",
                             "content": f"**[{node_name}]** {content}"}
                        )

    except Exception as exc:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"**[error]** {exc}"}
        )

    # Clear trace panel after completion
    status_placeholder.success(
        f"Terminé — {_step} étape(s) · {len(_all_files)} fichier(s) · "
        f"{_total_tokens['total']:,} tokens ({_total_tokens['prompt']:,} prompt + {_total_tokens['completion']:,} completion)"
    )
    tool_placeholder.empty()
    progress_placeholder.empty()

    st.rerun()
