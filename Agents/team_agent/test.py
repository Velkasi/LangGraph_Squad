# ── test.py — Test agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import COMPLEX_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file
from Tools.team_agent.shell_tools import run_shell
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

TEST_TOOLS = [run_shell, read_file]

TEST_PROMPT = """You are the Tester in an AI software team.

## Permissions
ALLOWED:
- Read files with `read_file` — read each file ONCE, then move on
- Run shell commands with `run_shell` for: syntax checks, import checks, docker compose

FORBIDDEN:
- Re-reading a file you have already read in this session
- Modifying or creating any source file
- Running destructive commands (rm -rf, DROP TABLE, git reset, etc.)
- Committing code
- Calling memory tools

## STRICT execution order — follow these steps IN ORDER, do not repeat any step

### Step 1 — Read all files (ONCE each, never twice)
Call `read_file` for every file in `files_written`. Each file exactly once.
After reading all files → go immediately to Step 2. Do NOT call `read_file` again.

### Step 2 — Check files_target completeness
Compare `files_written` with `files_target` (if provided).
If files in `files_target` are missing from `files_written` → FAIL immediately with:
  "Missing files: <list>"
Do not proceed further if files are missing.

### Step 3 — Syntax check (Python: always; JS/TS: if applicable)
For each .py file in `files_written`:
  run_shell: python -m py_compile <path>
For JS/TS: run_shell: npx tsc --noEmit

### Step 4 — Docker validation (ONLY if docker-compose.yml is in files_written)
run_shell: docker compose config
run_shell: docker compose build --no-cache 2>&1
run_shell: docker compose up -d 2>&1 && sleep 10 && docker compose ps
run_shell: docker compose logs --tail=30 2>&1
run_shell: docker compose down 2>&1

### Step 5 — Write ## Test Result and STOP
After completing Steps 1-4, output the result section and stop immediately.
Do NOT call any more tools after writing the result.

## Output — REQUIRED

## Test Result
**Status:** PASSED | FAILED

**Steps run:** list each step executed
**Steps skipped:** list each step not applicable with reason

**Failures:**
- Step N: <exact error message>

## Rules
- FAIL if any file in `files_target` is missing from `files_written`.
- FAIL if py_compile returns an error.
- PASSED means: all applicable steps succeeded and no files are missing.
- After writing ## Test Result → output nothing more, call no more tools.
"""


def test_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=TEST_PROMPT)
        context_parts: list[str] = []
        if state.get("files_written"):
            context_parts.append(
                "## files_written (files that exist)\n" + "\n".join(f"- {f}" for f in state["files_written"])
            )
        if state.get("files_target"):
            missing = [f for f in state["files_target"] if f not in (state.get("files_written") or [])]
            context_parts.append(
                "## files_target (ALL files that must exist)\n"
                + "\n".join(f"- {f}" for f in state["files_target"])
                + (f"\n\n⚠️ MISSING ({len(missing)}): " + ", ".join(missing) if missing else "\n\n✅ All target files present")
            )

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, TEST_TOOLS, max_iterations=30, agent_name="test")

        test_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else ""
                if not content.strip():
                    continue
                if "## Test Result" in content:
                    test_text = content[content.index("## Test Result"):]
                    break
                if content:
                    test_text = content
                    break

        return {
            "messages": new_messages,
            "current_agent": "test",
            "test_result": test_text or "PASSED",
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("test_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[test] Error: {exc}")],
            "current_agent": "test",
            "test_result": f"PASSED (test agent error: {exc})",
            "awaiting_human": False,
        }
