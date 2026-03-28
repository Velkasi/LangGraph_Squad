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

You have access to a Docker daemon. Execute all steps in order.

Stop immediately on failure, except for Step 8 which must always run.

## Step 1 — Static file checks
- Use `read_file` on every file in `files_written`.
- Verify each file is non-empty and plausible.
- Read `docker-compose.yml`.
- For each service with `build:`, confirm its Dockerfile exists using `read_file`.
- Verify every local `import` or `require` in JS/TS files resolves to an existing file.

If any file or dependency is missing → FAIL.

## Step 2 — Compose validation
run_shell:
docker compose config

## Step 3 — Docker build
run_shell:
docker compose build --no-cache 2>&1

## Step 4 — Start containers
run_shell:
docker compose up -d 2>&1

run_shell:
sleep 10 && docker compose ps

All services must show `running` or `healthy`.

## Step 5 — Logs check
run_shell:
docker compose logs --tail=30 2>&1

Fail if containers exited or show fatal errors.

## Step 6 — Database connectivity
run_shell:
docker compose exec backend node -e "const { Client } = require('pg'); const c = new Client({ connectionString: process.env.SUPABASE_DB_URL }); c.connect().then(() => { console.log('DB OK'); c.end(); }).catch(e => { console.error('DB FAIL', e.message); process.exit(1); })"

Fail if connection fails.

## Step 7 — HTTP endpoint check
run_shell:
docker compose exec backend curl -sf http://localhost:3000/api/public

Fail if request fails.

## Step 8 — Teardown (always run)
run_shell:
docker compose down 2>&1

## Output

## Test Result
**Status:** PASSED | FAILED

**Steps passed:** 1,2,3...

**Failures:**
- Step N: <exact error>

## Rules
- FAIL if any container exits unexpectedly.
- FAIL if a Dockerfile referenced by `build:` is missing.
- FAIL if database connection fails.
- Do not modify code.

## Tools
run_shell · read_file
"""


def test_node(state: AgentState) -> AgentState:
    try:
        system = SystemMessage(content=TEST_PROMPT)
        context_parts: list[str] = []
        if state.get("files_written"):
            context_parts.append(
                "## Files to test\n" + "\n".join(f"- {f}" for f in state["files_written"])
            )

        messages = [system]
        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))
        messages += state["messages"]

        new_messages, _, tokens = run_tool_loop(MODEL, MODEL_PROVIDER, messages, TEST_TOOLS, max_iterations=30, agent_name="test")

        test_text: str | None = None
        for msg in reversed(new_messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""
                if "## Test Result" in content:
                    test_text = content[content.index("## Test Result"):]
                elif content:
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
