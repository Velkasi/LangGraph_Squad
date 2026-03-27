# ── file_tools.py — Safe read/write tools scoped to WORKSPACE_DIR ────

from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.tools import tool
from Config.team_agent.config import WORKSPACE_DIR

logger = logging.getLogger(__name__)

_WORKSPACE = Path(WORKSPACE_DIR).resolve()


def _safe_path(relative_path: str) -> Path:
    """Resolve a relative path inside WORKSPACE_DIR and guard against path traversal."""
    resolved = (_WORKSPACE / relative_path).resolve()
    if not str(resolved).startswith(str(_WORKSPACE)):
        raise ValueError(f"Path traversal attempt blocked: {relative_path}")
    return resolved


@tool
def read_file(path: str) -> str:
    """Read the contents of a file inside the workspace directory.

    Args:
        path: Path relative to WORKSPACE_DIR.
    """
    try:
        full = _safe_path(path)
        return full.read_text(encoding="utf-8")
    except ValueError as exc:
        logger.warning("read_file blocked: %s", exc)
        return f"Error: {exc}"
    except FileNotFoundError:
        return f"Error: file not found — {path}"
    except Exception as exc:
        logger.warning("read_file failed for %s: %s", path, exc)
        return f"Error reading file: {exc}"


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file inside the workspace directory (creates parents if needed).

    Args:
        path: Path relative to WORKSPACE_DIR.
        content: Text content to write.
    """
    try:
        full = _safe_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return f"Written {len(content)} characters to {path}"
    except ValueError as exc:
        logger.warning("write_file blocked: %s", exc)
        return f"Error: {exc}"
    except Exception as exc:
        logger.warning("write_file failed for %s: %s", path, exc)
        return f"Error writing file: {exc}"
