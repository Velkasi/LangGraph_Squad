"""FastAPI backend — streams agent trace events over WebSocket."""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "04_Tracer")))

import asyncio
import json
import logging
import threading
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("server")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, ToolMessage

from Graph.team_agent.graph import graph
from agent_trace import get_builder, reset_builder, to_json as record_to_json, save_json, save_markdown
from agent_trace.mermaid import events_to_mermaid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_SENTINEL = object()  # signals end of stream


def _events_as_dicts(events) -> list[dict]:
    return [{"ts": e.ts, "kind": e.kind, "agent": e.agent, "payload": e.payload} for e in events]


def _run_graph_in_thread(init: dict, config: dict, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Run graph.stream() synchronously in a thread, pushing chunks into the async queue."""
    try:
        for chunk in graph.stream(init, config=config):
            asyncio.run_coroutine_threadsafe(queue.put(("chunk", chunk)), loop).result()
    except Exception as exc:
        asyncio.run_coroutine_threadsafe(queue.put(("error", exc)), loop).result()
    finally:
        asyncio.run_coroutine_threadsafe(queue.put(("done", None)), loop).result()


@app.websocket("/ws")
async def websocket_run(ws: WebSocket):
    await ws.accept()
    log.info("WebSocket accepted")

    try:
        raw = await ws.receive_text()
        data = json.loads(raw)
        prompt = data.get("prompt", "")
        thread_id = data.get("thread_id", str(uuid.uuid4()))
    except Exception as exc:
        await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
        return

    log.info("Run start — prompt=%r thread=%s", prompt[:80], thread_id[:8])

    from Config.team_agent.config import WORKSPACE_DIR

    reset_builder(
        workspace_dir=WORKSPACE_DIR,
        task=prompt,
        session_id=f"ws://{thread_id}",
    )

    config = {"configurable": {"thread_id": thread_id}}
    init = {
        "messages": [HumanMessage(content=prompt)],
        "task": prompt, "current_agent": "", "files_written": [],
        "awaiting_human": False, "plan": None, "arch_decision": None,
        "review_result": None, "test_result": None, "writeup_done": False,
        "dev_attempts": 0, "token_usage": None,
    }

    files: list[str] = []
    messages_out: list[dict] = []
    messages_sent_idx: int = 0   # track how many messages already sent to client
    stream_error: str = ""

    # ── Run graph in background thread, consume via async queue ──────────────
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    thread = threading.Thread(
        target=_run_graph_in_thread, args=(init, config, queue, loop), daemon=True
    )
    thread.start()

    while True:
        kind, payload = await queue.get()

        if kind == "error":
            stream_error = str(payload)
            log.error("graph.stream error: %s", payload, exc_info=payload)
            try:
                await ws.send_text(json.dumps({"type": "error", "message": stream_error}))
            except Exception:
                pass
            break

        if kind == "done":
            log.info("graph.stream finished")
            break

        # kind == "chunk"
        chunk = payload
        for node, out in chunk.items():
            if node in ("__end__", "__interrupt__") or not isinstance(out, dict):
                continue

            for f in out.get("files_written") or []:
                if f not in files:
                    files.append(f)

            for m in out.get("messages", []):
                c = m.content if hasattr(m, "content") else str(m)
                if c and not isinstance(m, ToolMessage):
                    messages_out.append({"role": "assistant", "node": node, "content": c})

            events_snap = _events_as_dicts(get_builder().events)
            mermaid_str = ""
            try:
                mermaid_str = events_to_mermaid(get_builder().events)
            except Exception:
                pass

            # Only send NEW messages (not already sent in previous steps)
            new_msgs = messages_out[messages_sent_idx:]
            messages_sent_idx = len(messages_out)

            log.info("STEP  node=%-14s events=%d new_msgs=%d files=%d",
                     node, len(events_snap), len(new_msgs), len(files))

            try:
                await ws.send_text(json.dumps({
                    "type": "step",
                    "node": node,
                    "events": events_snap,
                    "mermaid": mermaid_str,
                    "files": list(files),
                    "token_usage": out.get("token_usage") or {},
                    "messages": new_msgs,
                }))
            except WebSocketDisconnect:
                log.warning("Client disconnected during step")
                return

    thread.join(timeout=5)

    # ── Build final record ────────────────────────────────────────────────────
    captured = list(get_builder().events)
    record_json = ""
    export_msg = f"{len(captured)} événements capturés"
    try:
        record = get_builder().build_record(files_written=files)
        record_json = record_to_json(record)
        trace_dir = Path(WORKSPACE_DIR) / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        sid = thread_id[:8]
        jp = save_json(record, trace_dir / f"{sid}_trace.json")
        mp = save_markdown(record, captured, trace_dir / f"{sid}_trace.md", task=prompt)
        export_msg = f"Trace saved → {jp.name} + {mp.name}"
    except Exception as exc:
        log.error("Trace export failed: %s", exc, exc_info=True)
        export_msg = f"Trace export failed: {exc}"

    final_mermaid = ""
    try:
        final_mermaid = events_to_mermaid(get_builder().events)
    except Exception:
        pass

    log.info("DONE  events=%d msgs=%d files=%d record_len=%d  export=%s",
             len(captured), len(messages_out), len(files), len(record_json), export_msg)

    try:
        await ws.send_text(json.dumps({
            "type": "done",
            "events": _events_as_dicts(captured),
            "mermaid": final_mermaid,
            "record_json": record_json,
            "messages": messages_out,
            "files": files,
            "export_msg": export_msg,
        }))
        log.info("DONE sent OK")
    except WebSocketDisconnect:
        log.warning("Client disconnected before DONE could be sent")
    except Exception as exc:
        log.error("Failed to send DONE: %s", exc)
