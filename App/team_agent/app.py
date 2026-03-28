# ── app.py ────────────────────────────────────────────────────────────────────

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "04_Tracer")))

import json, uuid
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from Graph.team_agent.graph import graph
from agent_trace import get_builder, reset_builder, to_json as record_to_json, save_json, save_markdown
from agent_trace.mermaid import events_to_mermaid
from agent_trace.schema import TraceEvent


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_events(raw: list) -> list[TraceEvent]:
    return [
        e if isinstance(e, TraceEvent)
        else TraceEvent(ts=e["ts"], kind=e["kind"], agent=e["agent"], payload=e["payload"])
        for e in raw
    ]

def _mermaid_html(mermaid_str: str) -> str:
    return (
        "<html><head>"
        "<script src='https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'></script>"
        "<script>mermaid.initialize({startOnLoad:true,theme:'default'});</script>"
        "<style>body{margin:0;padding:8px;background:#fafafa;}.mermaid svg{max-width:100%;}</style>"
        "</head><body><div class='mermaid'>" + mermaid_str + "</div></body></html>"
    )


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Team Agent", page_icon="🤖", layout="wide")


# ── Session state ─────────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "graph_config" not in st.session_state:
    st.session_state.graph_config = {"configurable": {"thread_id": st.session_state.thread_id}}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_events" not in st.session_state:
    st.session_state.last_events = []
if "last_record_json" not in st.session_state:
    st.session_state.last_record_json = None
if "last_task" not in st.session_state:
    st.session_state.last_task = ""
if "last_tokens" not in st.session_state:
    st.session_state.last_tokens = {"prompt": 0, "completion": 0, "total": 0}


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Team Agent")
    st.caption("LangGraph · Streamlit")
    st.divider()
    st.subheader("Session")
    st.code(st.session_state.thread_id[:8] + "…", language=None)
    if st.button("New session", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.graph_config = {"configurable": {"thread_id": st.session_state.thread_id}}
        st.session_state.messages = []
        st.session_state.last_events = []
        st.session_state.last_record_json = None
        st.session_state.last_task = ""
        st.session_state.last_tokens = {"prompt": 0, "completion": 0, "total": 0}
        st.rerun()
    st.divider()
    st.caption(f"Trace events: **{len(st.session_state.last_events)}**")
    try:
        snap = graph.get_state(st.session_state.graph_config)
        vals = snap.values if snap else {}
        st.write("Agent:", vals.get("current_agent", "—"))
        st.write("Files:", len(vals.get("files_written") or []))
    except Exception:
        st.write("(no state)")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_chat, tab_diagram, tab_record, tab_log = st.tabs([
    "💬 Chat", "📊 Sequence Diagram", "🔬 Agent Trace (v1)", "📋 Event Log",
])


# ── TAB 1 — Chat ──────────────────────────────────────────────────────────────

with tab_chat:
    # Affiche l'historique
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Describe the task for the team…")

    if prompt:
        from Config.team_agent.config import WORKSPACE_DIR

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.last_task = prompt

        with st.chat_message("user"):
            st.markdown(prompt)

        reset_builder(
            workspace_dir=WORKSPACE_DIR,
            task=prompt,
            session_id=f"local://session/{st.session_state.thread_id}",
        )

        # Placeholders live — dans le tab_chat
        _ICONS = {
            "planner": "📋", "architect": "🏗️", "dev": "💻", "test": "🧪",
            "debug": "🐛", "reviewer": "🔍", "writeup": "📝", "analyst": "📊", "supervisor": "🎯",
        }
        st.divider()
        st.caption("**Live trace**")
        col_l, col_r = st.columns([1, 2])
        with col_l:
            ph_status = st.empty()
            ph_tools  = st.empty()
            ph_files  = st.empty()
            ph_tokens = st.empty()
            ph_step   = st.empty()
        with col_r:
            st.caption("Sequence diagram (live)")
            ph_diagram = st.empty()

        _files: list[str] = []
        _step = 0
        _tokens = {"prompt": 0, "completion": 0, "total": 0}
        _tools_seen: list[str] = []

        def _live_diagram():
            try:
                mstr = events_to_mermaid(get_builder().events)
                ph_diagram.html(_mermaid_html(mstr), height=500, scrolling=True)
            except Exception:
                pass

        def _live_panel(agent: str):
            ph_status.markdown(f"**{_ICONS.get(agent,'🤖')} Agent actif :** `{agent}`")
            if _tools_seen:
                ph_tools.markdown("**Outils :**\n" + "\n".join(f"- `{t}`" for t in _tools_seen[-5:]))
            if _files:
                ph_files.markdown("**Fichiers :**\n" + "\n".join(f"- `{f}`" for f in _files))
            ph_tokens.markdown(
                f"**Tokens** — in: `{_tokens['prompt']:,}` out: `{_tokens['completion']:,}` "
                f"**total: `{_tokens['total']:,}`**"
            )
            ph_step.caption(f"Étape {_step}")

        # Run graph
        try:
            init = {
                "messages": [HumanMessage(content=prompt)],
                "task": prompt, "current_agent": "", "files_written": [],
                "awaiting_human": False, "plan": None, "arch_decision": None,
                "review_result": None, "test_result": None, "writeup_done": False,
                "dev_attempts": 0, "token_usage": None,
            }
            for chunk in graph.stream(init, config=st.session_state.graph_config):
                for node, out in chunk.items():
                    if node in ("__end__", "__interrupt__") or not isinstance(out, dict):
                        continue
                    _step += 1
                    msgs = out.get("messages", [])
                    for m in msgs:
                        if isinstance(m, AIMessage):
                            for tc in (getattr(m, "tool_calls", None) or []):
                                n = tc.get("name") if isinstance(tc, dict) else tc.name
                                if n and n not in _tools_seen:
                                    _tools_seen.append(n)
                    for f in out.get("files_written") or []:
                        if f not in _files:
                            _files.append(f)
                    u = out.get("token_usage") or {}
                    _tokens["prompt"]     += u.get("prompt_tokens", 0)
                    _tokens["completion"] += u.get("completion_tokens", 0)
                    _tokens["total"]      += u.get("total_tokens", 0)
                    _live_panel(node)
                    _live_diagram()
                    for m in msgs:
                        c = m.content if hasattr(m, "content") else str(m)
                        if c and not isinstance(m, ToolMessage):
                            st.session_state.messages.append(
                                {"role": "assistant", "content": f"**[{node}]** {c}"}
                            )
        except Exception as exc:
            st.session_state.messages.append({"role": "assistant", "content": f"**[error]** {exc}"})

        # ── Sauvegarde trace dans session_state ───────────────────────────────
        captured = list(get_builder().events)
        st.session_state.last_events = [
            {"ts": e.ts, "kind": e.kind, "agent": e.agent, "payload": dict(e.payload)}
            for e in captured
        ]
        st.session_state.last_tokens = dict(_tokens)

        export_msg = f"{len(captured)} événements capturés"
        try:
            record = get_builder().build_record(files_written=_files)
            st.session_state.last_record_json = record_to_json(record)
            trace_dir = Path(WORKSPACE_DIR) / "traces"
            sid = st.session_state.thread_id[:8]
            jp = save_json(record, trace_dir / f"{sid}_trace.json")
            mp = save_markdown(record, captured, trace_dir / f"{sid}_trace.md", task=prompt)
            export_msg = f"Trace saved → `{jp.name}` + `{mp.name}`"
        except Exception as exc:
            st.error(f"Trace export failed: {exc}")
            import traceback; traceback.print_exc()

        _live_diagram()
        ph_status.success(
            f"Terminé — {_step} étape(s) · {len(_files)} fichier(s) · {_tokens['total']:,} tokens"
        )
        ph_tools.empty()
        ph_step.caption(export_msg)

        # Rerun pour que les autres tabs voient les données
        st.rerun()


# ── TAB 2 — Sequence Diagram ──────────────────────────────────────────────────

with tab_diagram:
    st.subheader("Sequence Diagram")
    raw = st.session_state.last_events
    if not raw:
        st.info("Lancez une tâche dans l'onglet Chat pour voir le diagramme.")
    else:
        events = _to_events(raw)
        st.success(f"{len(events)} événements — *{st.session_state.last_task}*")
        mstr = events_to_mermaid(events)
        st.download_button("Télécharger .md", "```mermaid\n" + mstr + "\n```",
                           file_name="sequence_diagram.md", mime="text/markdown")
        components.html(_mermaid_html(mstr), height=700, scrolling=True)
        with st.expander("Source Mermaid"):
            st.code(mstr, language="text")


# ── TAB 3 — Agent Trace v1 ────────────────────────────────────────────────────

with tab_record:
    st.subheader("Agent Trace Record — v1")
    rj = st.session_state.last_record_json
    if not rj:
        st.info("Lancez une tâche dans l'onglet Chat pour générer un trace record.")
    else:
        rd = json.loads(rj)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fichiers", len(rd.get("files", [])))
        c2.metric("Ranges", sum(
            len(s.get("ranges", []))
            for f in rd.get("files", [])
            for s in f.get("sessions", [])
        ))
        tok = st.session_state.last_tokens
        c3.metric("Tokens", f"{tok['total']:,}")
        git = rd.get("git") or {}
        rev = git.get("revision", "—")
        c4.metric("Git SHA", rev[:12] if rev != "—" else "—")

        st.divider()
        files = rd.get("files", [])
        if files:
            rows = []
            for f in files:
                for s in f.get("sessions", []):
                    for r in s.get("ranges", []):
                        ch = r.get("content_hash") or "—"
                        rows.append({
                            "Fichier": f["path"], "Agent": s.get("agent", "?"),
                            "Modèle": s.get("model", "?"),
                            "Lignes": f"{r['start_line']}–{r['end_line']}",
                            "Hash": ch[:24] + "…" if len(ch) > 24 else ch,
                        })
            st.dataframe(rows, use_container_width=True)
        else:
            st.write("Aucun fichier attribué.")

        ts = rd.get("metadata", {}).get("token_summary", {})
        if ts:
            st.dataframe([
                {"Agent": a, "Modèle": d.get("model", "?"), "Appels": d.get("calls", 0),
                 "Prompt": d.get("prompt", 0), "Completion": d.get("completion", 0),
                 "Total": d.get("total", 0)}
                for a, d in ts.items()
            ], use_container_width=True)

        st.divider()
        st.download_button("Télécharger trace.json", rj,
                           file_name="agent_trace.json", mime="application/json")
        st.json(rd, expanded=2)


# ── TAB 4 — Event Log ─────────────────────────────────────────────────────────

with tab_log:
    st.subheader("Full Event Log")
    raw = st.session_state.last_events
    if not raw:
        st.info("Lancez une tâche dans l'onglet Chat pour voir le log d'événements.")
    else:
        events = _to_events(raw)
        st.success(f"{len(events)} événements — *{st.session_state.last_task}*")

        c1, c2 = st.columns(2)
        sel_agents = c1.multiselect("Agents", sorted({e.agent for e in events}),
                                    default=sorted({e.agent for e in events}))
        sel_kinds  = c2.multiselect("Types", sorted({e.kind for e in events}),
                                    default=sorted({e.kind for e in events}))
        filtered = [e for e in events if e.agent in sel_agents and e.kind in sel_kinds]
        st.caption(f"{len(filtered)} / {len(events)}")

        ICONS = {
            "llm_call": "🔵", "llm_response": "🟢", "tool_call": "🟡", "tool_result": "🟠",
            "memory_op": "🟣", "supervisor_route": "🎯", "agent_start": "▶",
            "agent_done": "✅", "error": "❌",
        }
        for i, ev in enumerate(filtered, 1):
            p = ev.payload
            if ev.kind == "llm_call":
                detail = f"model=`{p.get('model','?')}` | in={p.get('prompt_tokens',0):,} out={p.get('completion_tokens',0):,} tot={p.get('total_tokens',0):,}"
            elif ev.kind == "llm_response":
                detail = "+tools" if p.get("has_tool_calls") else "text only"
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
                f"`{i:03d}` `{ev.ts}` {ICONS.get(ev.kind,'•')} **{ev.agent}** · `{ev.kind}`  \n"
                f"&nbsp;&nbsp;&nbsp;&nbsp;{detail}"
            )
