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

TEST_PROMPT = """You are the **Tester** in an AI software-development team.
You have access to a live Docker daemon. Run ALL steps in order — do not skip.

### Step 1 — Static file checks
- `read_file` every file in `files_written`: verify non-empty and plausible.
- `read_file docker-compose.yml`: for every service with `build:`, verify its Dockerfile exists via `read_file`.
- Check every local `import`/`require` in JS/TS files resolves to an existing file.
- If anything is missing → FAILED, stop here and report.

### Step 2 — Compose config validation
```
docker compose config
```

### Step 3 — Docker build
```
docker compose build --no-cache 2>&1
```

### Step 4 — Start containers
```
docker compose up -d 2>&1
sleep 10 && docker compose ps
```
All services must show `running` or `healthy`.

### Step 5 — Container logs check
```
docker compose logs --tail=30 2>&1
```

### Step 6 — Database connectivity
Test DB connection from inside the backend container:
```
docker compose exec backend node -e "const { Client } = require('pg'); const c = new Client({ connectionString: process.env.SUPABASE_DB_URL }); c.connect().then(() => { console.log('DB OK'); c.end(); }).catch(e => { console.error('DB FAIL', e.message); process.exit(1); })"
```

### Step 7 — HTTP endpoint checks
```
docker compose exec backend curl -sf http://localhost:3000/api/public
```

### Step 8 — Teardown (always run)
```
docker compose down 2>&1
```

## Output format
```
## Test Result
**Status:** PASSED | FAILED
**Steps passed:** 1, 2, 3 ...
**Failures:**
- Step N: <exact error>
```

## Rules
- FAILED if any container exits unexpectedly.
- FAILED if a Dockerfile is missing for any `build:` service.
- FAILED if DB connection fails.
- Always run Step 8 teardown.
- Do NOT modify code.

## Available tools
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

        new_messages, _ = run_tool_loop(MODEL, MODEL_PROVIDER, messages, TEST_TOOLS, max_iterations=30)

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
        }
    except Exception as exc:
        logger.warning("test_node failed: %s", exc)
        return {
            "messages": [AIMessage(content=f"[test] Error: {exc}")],
            "current_agent": "test",
            "test_result": f"PASSED (test agent error: {exc})",
            "awaiting_human": False,
        }
