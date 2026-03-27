# ── shell_tools.py — Safe shell execution for tests, lint, and build commands ────

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from Config.team_agent.config import SHELL_TIMEOUT_SECONDS, WORKSPACE_DIR

logger = logging.getLogger(__name__)

_WORKSPACE = Path(WORKSPACE_DIR).resolve()

# Commands that are never allowed regardless of context
_BLOCKED_PREFIXES = ("rm -rf", "rmdir /s", "shutdown", "reboot", "mkfs", "dd if=")


def _is_blocked(command: str) -> bool:
    lower = command.strip().lower()
    return any(lower.startswith(prefix) for prefix in _BLOCKED_PREFIXES)


@tool
def run_shell(command: str) -> str:
    """Execute a shell command inside the workspace directory and return its output.

    Intended for safe operations: running tests, lint checks, build scripts.
    Destructive commands (rm -rf, etc.) are blocked.

    Args:
        command: Shell command string to execute.
    """
    if _is_blocked(command):
        logger.warning("run_shell blocked dangerous command: %s", command)
        return f"Error: command blocked for safety reasons — {command}"
    try:
        _WORKSPACE.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(_WORKSPACE),
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        output = result.stdout or ""
        errors = result.stderr or ""
        combined = (output + ("\n[stderr]\n" + errors if errors else "")).strip()
        return combined if combined else f"(exit code {result.returncode}, no output)"
    except subprocess.TimeoutExpired:
        logger.warning("run_shell timed out: %s", command)
        return f"Error: command timed out after {SHELL_TIMEOUT_SECONDS}s"
    except Exception as exc:
        logger.warning("run_shell failed: %s", exc)
        return f"Error executing command: {exc}"
