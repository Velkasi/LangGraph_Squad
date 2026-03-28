# ── git_tools.py — Git diff and commit tools scoped to WORKSPACE_DIR ────

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from Config.team_agent.config import WORKSPACE_DIR

logger = logging.getLogger(__name__)

_WORKSPACE = Path(WORKSPACE_DIR).resolve()


def _git(args: list[str], check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(_WORKSPACE),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=check,
        timeout=30,
    )


@tool
def git_diff(staged: bool = False) -> str:
    """Show the current git diff for the workspace.

    Args:
        staged: If True show staged changes; otherwise show unstaged changes.
    """
    try:
        args = ["diff"]
        if staged:
            args.append("--staged")
        result = _git(args)
        output = result.stdout.strip()
        return output if output else "No changes detected."
    except FileNotFoundError:
        return "Error: git not found in PATH."
    except subprocess.TimeoutExpired:
        return "Error: git diff timed out."
    except Exception as exc:
        logger.warning("git_diff failed: %s", exc)
        return f"Error running git diff: {exc}"


@tool
def git_commit(message: str, add_all: bool = True) -> str:
    """Stage all changes and create a git commit in the workspace.

    Args:
        message: Commit message.
        add_all: If True run 'git add -A' before committing.
    """
    try:
        if add_all:
            add_result = _git(["add", "-A"])
            if add_result.returncode != 0:
                logger.warning("git add failed: %s", add_result.stderr)
                return f"Error staging files: {add_result.stderr.strip()}"

        commit_result = _git(["commit", "-m", message])
        if commit_result.returncode == 0:
            return commit_result.stdout.strip() or "Commit created successfully."
        stderr = commit_result.stderr.strip()
        # Nothing to commit is not an error
        if "nothing to commit" in stderr.lower():
            return "Nothing to commit — working tree clean."
        logger.warning("git commit failed: %s", stderr)
        return f"Error creating commit: {stderr}"
    except FileNotFoundError:
        return "Error: git not found in PATH."
    except subprocess.TimeoutExpired:
        return "Error: git commit timed out."
    except Exception as exc:
        logger.warning("git_commit failed: %s", exc)
        return f"Error running git commit: {exc}"
