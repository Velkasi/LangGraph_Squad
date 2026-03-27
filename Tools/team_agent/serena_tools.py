# ── serena_tools.py — Serena MCP tools with persistent session ────
#
# Serena runs as a stdio MCP server spawned via uvx.
# The MCP session must stay open for tools to be callable after loading.
# We keep one persistent session alive in a background event loop thread.

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

_WHITELIST = {
    "find_symbol",
    "find_referencing_symbols",
    "search_for_pattern",
}

# ── Global state ─────────────────────────────────────────────────────────────
_tools: list = []
_load_lock = threading.Lock()
_loaded = False
_background_loop: asyncio.AbstractEventLoop | None = None


def _workspace() -> str:
    return os.path.abspath(os.environ.get("WORKSPACE_DIR", "./workspace"))


def _serena_args() -> list[str]:
    return [
        "--from", "git+https://github.com/oraios/serena",
        "serena", "start-mcp-server",
        "--context", "claude-code",
        "--project", _workspace(),
        "--enable-web-dashboard", "false",
    ]


def _get_loop() -> asyncio.AbstractEventLoop:
    global _background_loop
    if _background_loop is None or not _background_loop.is_running():
        loop = asyncio.new_event_loop()
        t = threading.Thread(target=loop.run_forever, daemon=True, name="serena-loop")
        t.start()
        _background_loop = loop
    return _background_loop


def _run_async(coro, timeout: int = 180) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro, _get_loop())
    return future.result(timeout=timeout)


# ── Persistent session holder ─────────────────────────────────────────────────
# We open a session() context manager and never exit it — tools call back into
# the same live session whenever invoked.

_session_ready = threading.Event()
_session_tools: list = []
_session_error: Exception | None = None


async def _run_persistent_session():
    """Open a Serena session and hold it open forever."""
    global _session_tools, _session_error
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore

        client = MultiServerMCPClient({
            "serena": {
                "transport": "stdio",
                "command": "uvx",
                "args": _serena_args(),
            }
        })

        async with client.session("serena") as session:
            from langchain_mcp_adapters.tools import load_mcp_tools  # type: ignore
            all_tools = await load_mcp_tools(session)
            _session_tools = [t for t in all_tools if t.name in _WHITELIST]
            logger.info("Serena session ready — tools: %s", [t.name for t in _session_tools])
            _session_ready.set()
            # Keep the session alive indefinitely
            await asyncio.Event().wait()

    except Exception as exc:
        _session_error = exc
        _session_ready.set()  # unblock _ensure_loaded even on error


def _ensure_loaded() -> list:
    global _tools, _loaded

    if _loaded:
        return _tools

    with _load_lock:
        if _loaded:
            return _tools

        # Start the persistent session in the background loop
        asyncio.run_coroutine_threadsafe(_run_persistent_session(), _get_loop())

        # Wait for session to be ready (or fail)
        ready = _session_ready.wait(timeout=180)
        if not ready:
            logger.warning("Serena session timed out after 180s")
            _tools = []
        elif _session_error is not None:
            def _unwrap(e, depth=0):
                causes = getattr(e, "exceptions", None)
                if causes and depth < 10:
                    for sub in causes:
                        _unwrap(sub, depth + 1)
                else:
                    logger.warning("Serena error: %s: %s", type(e).__name__, e)
            _unwrap(_session_error)
            _tools = []
        else:
            _tools = _session_tools
            logger.info("Serena tools available: %s", [t.name for t in _tools])

        _loaded = True

    return _tools


def get_serena_tools() -> list:
    """Return Serena LangChain tools filtered to the whitelist (lazy-loaded)."""
    return _ensure_loaded()


def __getattr__(name: str) -> Any:
    if name in _WHITELIST:
        tool = next((t for t in _ensure_loaded() if t.name == name), None)
        if tool is not None:
            return tool
        raise AttributeError(f"Serena tool '{name}' not available")
    raise AttributeError(name)
