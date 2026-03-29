# ── dev.py — Developer agent ────

from __future__ import annotations
import logging
from langchain_core.messages import AIMessage, SystemMessage
from Agents.team_agent.state import AgentState
from Config.team_agent.config import COMPLEX_MODEL as MODEL, MODEL_PROVIDER
from Tools.team_agent.file_tools import read_file, write_file
from Tools.team_agent.git_tools import git_commit, git_diff
from Tools.team_agent.memory_tools import commit_to_identity, remember, recall
from Tools.team_agent.shell_tools import run_shell
from Tools.team_agent.tool_loop import run_tool_loop

logger = logging.getLogger(__name__)

DEV_TOOLS = [read_file, write_file, run_shell, git_diff, git_commit, remember, recall, commit_to_identity]

DEV_PROMPT = """You are the Developer in an AI software team.

## Core Rule
Communicate ONLY via tool calls.
Never output code, markdown, or file contents as text.

All files MUST be created or modified using `write_file`.
If N files are needed, call `write_file` N times.

## Permissions
ALLOWED:
- Read files with `read_file`
- Write or overwrite files with `write_file`
- Run quick sanity checks with `run_shell` (no destructive commands)
- Review changes with `git_diff`
- Commit with `git_commit`
- Store technical constraints with `remember`
- Retrieve prior constraints with `recall`
- Store cross-project preferences with `commit_to_identity` (confidence > 0.9 only)

FORBIDDEN:
- Modifying files not listed in the plan or arch_decision
- Running destructive shell commands (rm -rf, DROP TABLE, git reset --hard, etc.)
- Changing the architecture or tech stack
- Calling `git push` or any remote operation
- Writing test files (that is the test agent's role)
- Writing documentation files other than inline code comments
- Duplicating a file that already exists under a different path

## Inputs
- `plan`
- `arch_decision`
- `files_already_written` — files created in previous iterations

Follow them strictly. Do not redesign the system.

## Mandatory First Steps (in order)
1. Call `recall` to retrieve relevant constraints.
2. Check `files_already_written` vs `files_target`:
   - `files_target` = the COMPLETE list of files you must produce (from the plan).
   - `files_already_written` = files already created in previous iterations.
   - Files to create = `files_target` MINUS `files_already_written`.
   - If `files_already_written` is NON-EMPTY → call `read_file` on each listed file first.
3. Write EVERY file in `files_target` that is NOT already in `files_already_written`.
   - One `write_file` call per file. Do not skip any.
   - Never attempt `read_file` on a file you haven't written yet — it will fail.

## Workflow
1. `recall` — retrieve constraints
2. `read_file` each file in `files_already_written`
3. For EACH file in `files_target` not yet written → `write_file`
4. `git_diff` — review all changes
5. `git_commit` — commit with a concise message

## CRITICAL: No redundant rewrites
- Do NOT rewrite a file that is already in `files_already_written` unless it has a bug.
- Focus each iteration on the MISSING files from `files_target`.
- If all `files_target` files are written → go directly to `git_diff` + `git_commit`.

## Coherence Rules
- One entrypoint only — do not create two scripts that do the same thing.
- One requirements.txt only — do not create a second one in a subdirectory.
- One Dockerfile only — unless the plan explicitly calls for multiple services.
- All imports must resolve to files you have written or packages in requirements.txt.
- All environment variables used in code must appear in docker-compose.yml or .env.example.

## Memory rules (STRICT)
Use `remember` ONLY for:
- A technical constraint discovered during implementation
- A decision that will affect future agents
- A pattern established for this project

NEVER use `remember` for:
- Confirming files were created
- Status updates
- Repeating what is already in the plan or arch_decision

Use `commit_to_identity` ONLY for high-confidence cross-project preferences (confidence > 0.9).

## Docker Rules
- Every `build:` in `docker-compose.yml` must reference an existing Dockerfile.
- Every env var used in code must exist in `docker-compose.yml environment:` or `.env.example`.
- Dockerfile RUN lines with multi-line apt-get must use real backslash+newline, not \\n literals.

## Final Step
After all files are written:
1. run `git_diff`
2. run `git_commit` with a concise message.

## Tools
read_file · write_file · run_shell · git_diff · git_commit · remember · recall · commit_to_identity
"""


def _read_existing_files(files: list[str]) -> str:
    """Read current content of already-written files to inject into dev context."""
    from Tools.team_agent.file_tools import get_workspace
    from pathlib import Path
    parts = []
    workspace = get_workspace()
    for path in files:
        try:
            full = (workspace / path).resolve()
            content = full.read_text(encoding="utf-8", errors="replace")
            # Truncate very large files to stay within token budget
            if len(content) > 3000:
                content = content[:3000] + "\n...[truncated]"
            parts.append(f"### {path}\n```\n{content}\n```")
        except Exception:
            parts.append(f"### {path}\n(could not read)")
    return "\n\n".join(parts)


def dev_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=DEV_PROMPT)
        context_parts: list[str] = []

        if state.get("plan"):
            context_parts.append(f"## Plan\n{state['plan']}")
        if state.get("arch_decision"):
            context_parts.append(f"## Architecture decision\n{state['arch_decision']}")

        existing_files = list(state.get("files_written") or [])

        # Derive files_target from the plan: extract file paths mentioned in the plan
        target_files = list(state.get("files_target") or [])

        if target_files:
            missing = [f for f in target_files if f not in existing_files]
            context_parts.append(
                f"## files_target (ALL files you must produce)\n"
                + "\n".join(f"- {f}" for f in target_files)
                + f"\n\n## Files already written ({len(existing_files)}/{len(target_files)})\n"
                + ("\n".join(f"- {f}" for f in existing_files) if existing_files else "None")
                + f"\n\n## Files still MISSING — write these NOW ({len(missing)})\n"
                + ("\n".join(f"- {f}" for f in missing) if missing else "None — all files done, go to git_diff + git_commit")
            )
        elif existing_files:
            context_parts.append(
                f"## Files already written\n" + "\n".join(f"- {f}" for f in existing_files)
            )
        else:
            context_parts.append(
                "## Files already written\nNone — this is the first pass. "
                "Do NOT call read_file. Go directly to write_file for every required file."
            )

        if existing_files:
            file_contents = _read_existing_files(existing_files)
            context_parts.append(f"## Current file contents\n{file_contents}")

        # Only pass the last human message — not the full agent conversation history
        # which would drown the dev in planner/architect output
        from langchain_core.messages import HumanMessage
        human_msgs = [m for m in state["messages"] if isinstance(m, HumanMessage)]
        last_human = human_msgs[-1:] if human_msgs else state["messages"][-1:]

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += last_human

        new_messages, new_files, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, DEV_TOOLS, max_iterations=15, agent_name="dev")

        existing = list(state.get("files_written") or [])
        for path in new_files:
            if path not in existing:
                existing.append(path)

        wrote_something = len(existing) > len(state.get("files_written") or [])
        return {
            "messages": new_messages,
            "current_agent": "dev",
            "files_written": existing,
            "dev_attempts": 0 if wrote_something else (state.get("dev_attempts") or 0) + 1,
            "awaiting_human": False,
            "token_usage": tokens,
        }
    except Exception as exc:
        logger.warning("dev_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[dev] Error: {exc}")],
            "current_agent": "dev",
            "dev_attempts": (state.get("dev_attempts") or 0) + 1,
            "awaiting_human": False,
        }
