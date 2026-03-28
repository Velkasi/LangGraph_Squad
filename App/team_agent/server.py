"""FastAPI backend — streams agent trace events over WebSocket."""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "04_Tracer")))

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")
log = logging.getLogger("server")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

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


def _events_as_dicts(events) -> list[dict]:
    return [{"ts": e.ts, "kind": e.kind, "agent": e.agent, "payload": e.payload} for e in events]


@app.websocket("/ws")
async def websocket_run(ws: WebSocket):
    await ws.accept()

    try:
        raw = await ws.receive_text()
        data = json.loads(raw)
        prompt = data.get("prompt", "")
        thread_id = data.get("thread_id", str(uuid.uuid4()))
    except Exception as exc:
        await ws.send_text(json.dumps({"type": "error", "message": str(exc)}))
        await ws.close()
        return

    from Config.team_agent.config import WORKSPACE_DIR

    reset_builder(
        workspace_dir=WORKSPACE_DIR,
        task=prompt,
        session_id=f"ws://session/{thread_id}",
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

    stream_error: str = ""
    try:
        for chunk in graph.stream(init, config=config):
            for node, out in chunk.items():
                if node in ("__end__", "__interrupt__") or not isinstance(out, dict):
                    continue

                # Collect files
                for f in out.get("files_written") or []:
                    if f not in files:
                        files.append(f)

                # Collect assistant messages
                for m in out.get("messages", []):
                    c = m.content if hasattr(m, "content") else str(m)
                    if c and not isinstance(m, ToolMessage):
                        messages_out.append({"role": "assistant", "node": node, "content": c})

                # Stream current events snapshot after each node
                events_snap = _events_as_dicts(get_builder().events)
                mermaid_str = ""
                try:
                    mermaid_str = events_to_mermaid(get_builder().events)
                except Exception:
                    pass

                log.info("STEP node=%-14s events=%d msgs=%d files=%d tokens=%s",
                         node, len(events_snap), len(messages_out), len(files),
                         out.get("token_usage") or {})

                await ws.send_text(json.dumps({
                    "type": "step",
                    "node": node,
                    "events": events_snap,
                    "mermaid": mermaid_str,
                    "files": list(files),
                    "token_usage": out.get("token_usage") or {},
                    "messages": list(messages_out),
                }))

                await asyncio.sleep(0)

    except BaseException as exc:
        stream_error = str(exc)
        log.error("graph.stream error: %s", exc, exc_info=True)
        try:
            await ws.send_text(json.dumps({"type": "error", "message": stream_error}))
        except Exception:
            pass

    # Final — build record and send done (always, even after error)
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

    log.info("DONE  events=%d msgs=%d files=%d record_json_len=%d export=%s",
             len(captured), len(messages_out), len(files), len(record_json), export_msg)

    done_payload = {
        "type": "done",
        "events": _events_as_dicts(captured),
        "mermaid": final_mermaid,
        "record_json": record_json,
        "messages": messages_out,
        "files": files,
        "export_msg": export_msg,
    }
    try:
        await ws.send_text(json.dumps(done_payload))
        log.info("DONE sent — events=%d mermaid=%d record=%d",
                 len(done_payload["events"]), len(done_payload["mermaid"]),
                 len(done_payload["record_json"]))
    except Exception as exc:
        log.error("Failed to send DONE: %s", exc)
