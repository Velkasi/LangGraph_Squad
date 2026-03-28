# ── app.py — Streamlit interface: chat + live trace tabs ─────────────────────

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "04_Tracer")))

import json
import uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from Graph.team_agent.graph import graph
from agent_trace import get_builder, reset_builder, to_json as record_to_json, save_json, save_markdown
from agent_trace.mermaid import events_to_mermaid

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
    st.session_state.messages = []

if "graph_config" not in st.session_state:
    st.session_state.graph_config = {
        "configurable": {"thread_id": st.session_state.thread_id}
    }

if "last_record_json" not in st.session_state:
    st.session_state.last_record_json = None

if "last_events" not in st.session_state:
    st.session_state.last_events = []

if "last_task" not in st.session_state:
    st.session_state.last_task = ""

if "last_files" not in st.session_state:
    st.session_state.last_files = []

if "last_tokens" not in st.session_state:
    st.session_state.last_tokens = {"prompt": 0, "completion": 0, "total": 0}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Team Agent")
    st.caption("AI software-development team powered by LangGraph")
    st.divider()

    st.subheader("Session")
    st.code(st.session_state.thread_id[:8] + "…", language=None)

    if st.button("New session", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.graph_config = {"configurable": {"thread_id": st.session_state.thread_id}}
        st.session_state.messages = []
        st.session_state.last_record_json = None
        st.session_state.last_events = []
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
# Tabs
# ---------------------------------------------------------------------------

tab_chat, tab_diagram, tab_record, tab_log = st.tabs([
    "💬 Chat",
    "📊 Sequence Diagram",
    "🔬 Agent Trace (v1)",
    "📋 Event Log",
])

# ===========================================================================
# TAB 1 — Chat
# ===========================================================================

with tab_chat:
    st.subheader("Team Agent")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Describe the task for the team…")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # ── Reset builder for this run ─────────────────────────────────────
        from Config.team_agent.config import WORKSPACE_DIR
        builder = reset_builder(
            workspace_dir=WORKSPACE_DIR,
            task=prompt,
            session_id=f"local://session/{st.session_state.thread_id}",
        )
        st.session_state.last_task = prompt

        # ── Live trace panel ───────────────────────────────────────────────
        _AGENT_ICONS = {
            "planner": "📋", "architect": "🏗️", "dev": "💻",
            "test": "🧪", "debug": "🐛", "reviewer": "🔍",
            "writeup": "📝", "analyst": "📊", "supervisor": "🎯",
        }

        st.divider()
        st.caption("**Live trace**")
        col_left, col_right = st.columns([1, 2])

        with col_left:
            status_ph   = st.empty()
            tool_ph     = st.empty()
            files_ph    = st.empty()
            tokens_ph   = st.empty()
            step_ph     = st.empty()

        with col_right:
            st.caption("Sequence diagram (live)")
            diagram_ph = st.empty()

        _all_files: list[str] = []
        _step = 0
        _total_tokens = {"prompt": 0, "completion": 0, "total": 0}
        _tool_calls_seen: list[str] = []

        def _render_live_diagram() -> None:
            try:
                mermaid_str = events_to_mermaid(get_builder().events)
                html = (
                    "<html><head>"
                    "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>"
                    "<script>mermaid.initialize({startOnLoad:true,theme:'default'});</script>"
                    "<style>body{margin:0;padding:4px;background:#fafafa;}.mermaid svg{max-width:100%;}</style>"
                    "</head><body><div class='mermaid'>"
                    + mermaid_str +
                    "</div></body></html>"
                )
                with col_right:
                    components.html(html, height=500, scrolling=True)
            except Exception:
                pass

        def _render_trace_panel(agent: str) -> None:
            icon = _AGENT_ICONS.get(agent, "🤖")
            status_ph.markdown(f"**{icon} Agent actif :** `{agent}`")
            if _tool_calls_seen:
                tool_ph.markdown("**Outils :**\n" + "\n".join(f"- `{t}`" for t in _tool_calls_seen[-5:]))
            if _all_files:
                files_ph.markdown(
                    f"**Fichiers ({len(_all_files)}) :**\n" +
                    "\n".join(f"- `{f}`" for f in _all_files)
                )
            tokens_ph.markdown(
                f"**Tokens** — in: `{_total_tokens['prompt']:,}` "
                f"out: `{_total_tokens['completion']:,}` "
                f"**total: `{_total_tokens['total']:,}`**"
            )
            step_ph.caption(f"Étape {_step}")

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

            for chunk in graph.stream(initial_state, config=st.session_state.graph_config):
                for node_name, node_output in chunk.items():
                    if node_name in ("__end__", "__interrupt__") or not isinstance(node_output, dict):
                        continue

                    _step += 1

                    msgs = node_output.get("messages", [])
                    for m in msgs:
                        if isinstance(m, AIMessage):
                            for tc in getattr(m, "tool_calls", None) or []:
                                name = tc.get("name") if isinstance(tc, dict) else tc.name
                                if name and name not in _tool_calls_seen:
                                    _tool_calls_seen.append(name)

                    for f in node_output.get("files_written") or []:
                        if f not in _all_files:
                            _all_files.append(f)

                    usage = node_output.get("token_usage") or {}
                    _total_tokens["prompt"]     += usage.get("prompt_tokens", 0)
                    _total_tokens["completion"] += usage.get("completion_tokens", 0)
                    _total_tokens["total"]      += usage.get("total_tokens", 0)

                    _render_trace_panel(node_name)
                    _render_live_diagram()

                    for m in msgs:
                        content = m.content if hasattr(m, "content") else str(m)
                        if content and not isinstance(m, ToolMessage):
                            st.session_state.messages.append(
                                {"role": "assistant", "content": f"**[{node_name}]** {content}"}
                            )

        except Exception as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"**[error]** {exc}"})

        # ── Build and persist TraceRecord ──────────────────────────────────
        try:
            record = get_builder().build_record(files_written=_all_files)
            st.session_state.last_record_json = record_to_json(record)
            st.session_state.last_events = list(get_builder().events)
            st.session_state.last_files = list(_all_files)
            st.session_state.last_tokens = dict(_total_tokens)

            # Save files
            trace_dir = Path(WORKSPACE_DIR) / "traces"
            short_id = st.session_state.thread_id[:8]
            json_path = save_json(record, trace_dir / f"{short_id}_trace.json")
            md_path = save_markdown(record, get_builder().events, trace_dir / f"{short_id}_trace.md", task=prompt)
            _export_msg = f"Trace saved → `{json_path.name}` + `{md_path.name}`"
            st.session_state.trace_saved = True
        except Exception as exc:
            _export_msg = f"❌ Trace export failed: {exc}"
            st.error(f"Erreur lors de l'export du trace: {exc}")
            import traceback
            traceback.print_exc()

        # ── Final diagram ──────────────────────────────────────────────────
        _render_live_diagram()

        status_ph.success(
            f"Terminé — {_step} étape(s) · {len(_all_files)} fichier(s) · "
            f"{_total_tokens['total']:,} tokens"
        )
        tool_ph.empty()
        step_ph.caption(_export_msg)

        st.rerun()

# ===========================================================================
# TAB 2 — Sequence Diagram
# ===========================================================================

with tab_diagram:
    st.subheader("Sequence Diagram")
    
    # Debug: afficher l'état de la session
    if not st.session_state.last_events:
        st.warning(f"⚠️ Pas d'événements capturés. État de la session: {bool(st.session_state.last_events)} événements")
        st.info("Lancez une tâche dans l'onglet Chat pour voir le diagramme.")
    else:
        st.success(f"✅ {len(st.session_state.last_events)} événements capturés")
        events = st.session_state.last_events
        mermaid_str = events_to_mermaid(events)

        # Download button
        st.download_button(
            "⬇ Télécharger .md",
            data="```mermaid\n" + mermaid_str + "\n```",
            file_name="sequence_diagram.md",
            mime="text/markdown",
        )

        html = (
            "<html><head>"
            "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>"
            "<script>mermaid.initialize({startOnLoad:true,theme:'default',sequence:{useMaxWidth:false}});</script>"
            "<style>body{margin:0;padding:8px;background:#fafafa;}.mermaid svg{max-width:100%;}</style>"
            "</head><body><div class='mermaid'>"
            + mermaid_str +
            "</div></body></html>"
        )
        components.html(html, height=700, scrolling=True)

        with st.expander("Source Mermaid"):
            st.code(mermaid_str, language="text")

# ===========================================================================
# TAB 3 — Agent Trace Record (v1)
# ===========================================================================

with tab_record:
    st.subheader("Agent Trace Record — v1 specification")
    st.caption("Format: [github.com/Velkasi/TracerIA](https://github.com/Velkasi/TracerIA)")

    record_json = st.session_state.last_record_json
    if not record_json:
        st.warning(f"⚠️ Pas de trace record. État: {bool(st.session_state.last_record_json)}")
        st.info("Lancez une tâche dans l'onglet Chat pour générer un trace record.")
        
        # Debug: show raw session state
        if st.session_state.get("trace_saved"):
            st.error("⚠️ Le trace a été sauvegardé mais last_record_json est vide!")
    else:
        st.success(f"✅ Trace record généré")
        record_dict = json.loads(record_json)

        # ── Summary metrics ────────────────────────────────────────────────
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Fichiers attribués", len(record_dict.get("files", [])))
        with col2:
            total_ranges = sum(
                len(s.get("ranges", []))
                for f in record_dict.get("files", [])
                for s in f.get("sessions", [])
            )
            st.metric("Ranges attribués", total_ranges)
        with col3:
            tok = st.session_state.last_tokens
            st.metric("Tokens totaux", f"{tok['total']:,}")
        with col4:
            vcs = record_dict.get("vcs", {})
            rev = vcs.get("revision", "—")
            st.metric("Git SHA", rev[:12] if rev != "—" else "—")

        st.divider()

        # ── File attribution table ─────────────────────────────────────────
        st.subheader("Attribution par fichier")

        files = record_dict.get("files", [])
        if files:
            rows = []
            for f in files:
                for sess in f.get("sessions", []):
                    agent    = sess.get("agent", "?")
                    model_id = sess.get("model", "?")
                    for r in sess.get("ranges", []):
                        ch = r.get("content_hash", "—") or "—"
                        rows.append({
                            "Fichier": f["path"],
                            "Agent":   agent,
                            "Modèle":  model_id,
                            "Lignes":  f"{r['start_line']}–{r['end_line']}",
                            "Hash":    ch[:24] + "…" if len(ch) > 24 else ch,
                        })
            st.dataframe(rows, use_container_width=True)
        else:
            st.write("Aucun fichier attribué.")

        st.divider()

        # ── Token usage per agent ──────────────────────────────────────────
        st.subheader("Tokens par agent")
        token_summary = record_dict.get("metadata", {}).get("token_summary", {})
        if token_summary:
            token_rows = [
                {
                    "Agent": agent,
                    "Modèle": data.get("model", "?"),
                    "Appels LLM": data.get("calls", 0),
                    "Prompt": data.get("prompt", 0),
                    "Completion": data.get("completion", 0),
                    "Total": data.get("total", 0),
                }
                for agent, data in token_summary.items()
            ]
            st.dataframe(token_rows, use_container_width=True)

        st.divider()

        # ── Raw JSON ───────────────────────────────────────────────────────
        st.subheader("JSON brut (Agent Trace v1)")
        st.download_button(
            "⬇ Télécharger trace.json",
            data=record_json,
            file_name="agent_trace.json",
            mime="application/json",
        )
        st.json(record_dict, expanded=2)

# ===========================================================================
# TAB 4 — Event Log
# ===========================================================================

with tab_log:
    st.subheader("Full Event Log")

    events = st.session_state.last_events
    if not events:
        st.warning(f"⚠️ Pas d'événements. État: {len(events)} événements trouvés")
        st.info("Lancez une tâche dans l'onglet Chat pour voir le log d'événements.")
    else:
        st.success(f"✅ {len(events)} événements capturés")
        # ── Filters ────────────────────────────────────────────────────────
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            all_agents = sorted({ev.agent for ev in events})
            selected_agents = st.multiselect("Agents", all_agents, default=all_agents)
        with col_f2:
            all_kinds = sorted({ev.kind for ev in events})
            selected_kinds = st.multiselect("Types d'événement", all_kinds, default=all_kinds)

        filtered = [
            ev for ev in events
            if ev.agent in selected_agents and ev.kind in selected_kinds
        ]

        st.caption(f"{len(filtered)} / {len(events)} événements")

        # ── Event rows ─────────────────────────────────────────────────────
        _KIND_COLORS = {
            "llm_call":        "🔵",
            "llm_response":    "🟢",
            "tool_call":       "🟡",
            "tool_result":     "🟠",
            "memory_op":       "🟣",
            "supervisor_route":"🎯",
            "agent_start":     "▶",
            "agent_done":      "✅",
            "error":           "❌",
        }

        for i, ev in enumerate(filtered, 1):
            icon = _KIND_COLORS.get(ev.kind, "•")
            p = ev.payload

            # Build detail string
            if ev.kind == "llm_call":
                detail = (
                    f"model=`{p.get('model','?')}` iter={p.get('iteration',1)} "
                    f"| in={p.get('prompt_tokens',0):,} "
                    f"out={p.get('completion_tokens',0):,} "
                    f"tot={p.get('total_tokens',0):,}"
                )
            elif ev.kind == "llm_response":
                detail = "+ tool_calls" if p.get("has_tool_calls") else "text only"
            elif ev.kind == "tool_call":
                detail = f"`{p.get('tool','?')}` — {p.get('args_summary','')}"
            elif ev.kind == "tool_result":
                detail = f"`{p.get('tool','?')}` → {p.get('result','')}"
            elif ev.kind == "memory_op":
                detail = f"`{p.get('operation','?')}` [{p.get('layer','?')}] {p.get('summary','')}"
            elif ev.kind == "supervisor_route":
                detail = f"→ `{p.get('target','?')}`"
            elif ev.kind == "agent_done":
                detail = f"{p.get('duration_ms',0):,}ms"
            elif ev.kind == "error":
                detail = p.get("message", "")
            else:
                detail = str(p)

            st.markdown(
                f"`{i:03d}` `{ev.ts}` {icon} **{ev.agent}** · `{ev.kind}`  \n"
                f"&nbsp;&nbsp;&nbsp;&nbsp;{detail}"
            )
