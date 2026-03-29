# ── tool_loop.py — Shared tool execution loop for all agent nodes ────

from __future__ import annotations

import logging
import os
import time

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from agent_trace import get_builder as get_tracer

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 30
_MAX_MSG_CHARS = 6_000    # ~1.5K tokens par message
_MAX_HISTORY_MESSAGES = 4
_MAX_TOOL_RESULT_CHARS = 2_000  # tool results tronqués plus agressivement

_last_call_time: dict[str, float] = {}  # api_key → timestamp dernier appel

# Cerebras TPM limits per model (tokens/minute, sliding window)
_CEREBRAS_TPM: dict[str, int] = {
    "llama3.1-8b":                    60_000,
    "qwen-3-235b-a22b-instruct-2507": 30_000,
}
_CEREBRAS_RPM = 30  # shared across all models on the same key

# Token usage sliding window: api_key → list of (timestamp, tokens_used)
_token_window: dict[str, list[tuple[float, int]]] = {}


def _tpm_wait(api_key: str, model: str, estimated_tokens: int) -> float:
    """Return seconds to wait before next call to stay within TPM + RPM limits.

    Uses a 60-second sliding window of recent token usage.
    """
    tpm_limit = _CEREBRAS_TPM.get(model, 30_000)
    window = _token_window.setdefault(api_key, [])
    now = time.monotonic()

    # Drop entries older than 60s
    window[:] = [(t, tok) for t, tok in window if now - t < 60.0]

    tokens_in_window = sum(tok for _, tok in window)

    # How many tokens remain before hitting TPM?
    remaining_tpm = tpm_limit - tokens_in_window

    wait_tpm = 0.0
    if remaining_tpm < estimated_tokens and window:
        # Wait until the oldest entry leaves the 60s window
        oldest_ts = window[0][0]
        wait_tpm = max(0.0, 60.0 - (now - oldest_ts) + 0.5)

    # RPM throttle: min 2s between calls (30 RPM → 1 per 2s, 10% margin)
    last = _last_call_time.get(api_key, 0.0)
    wait_rpm = max(0.0, 2.2 - (now - last))

    return max(wait_tpm, wait_rpm)


def _record_tokens(api_key: str, tokens_used: int) -> None:
    """Record token usage for the sliding window after a successful call."""
    window = _token_window.setdefault(api_key, [])
    window.append((time.monotonic(), tokens_used))
    _last_call_time[api_key] = time.monotonic()


def _get_api_keys() -> list[str]:
    """Retourne les clés disponibles — Cerebras/OpenRouter (clé unique) ou Groq (rotation)."""
    try:
        from Config.team_agent.config import CEREBRAS_API_KEY, OPENROUTER_API_KEY, _GROQ_KEYS
        if CEREBRAS_API_KEY:
            return [CEREBRAS_API_KEY]
        if OPENROUTER_API_KEY:
            return [OPENROUTER_API_KEY]
        return list(_GROQ_KEYS)
    except Exception:
        k = os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY", "")
        return [k] if k else []


def _get_openrouter_models() -> list[str]:
    """Retourne la liste des modèles OpenRouter en rotation (vide si Cerebras ou Groq)."""
    try:
        from Config.team_agent.config import OPENROUTER_MODELS
        return list(OPENROUTER_MODELS)
    except Exception:
        pass
    return []


def _build_llm(model: str, provider: str, tools: list, api_key: str):
    """Crée un LLM frais avec la clé donnée.

    Pour OpenRouter : provider=openai + OPENAI_API_BASE déjà défini dans config.
    max_retries=0 désactive le retry interne de LangChain/httpx.
    """
    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
        base_url = os.environ.get("OPENAI_API_BASE", "https://api.cerebras.ai/v1")
        return init_chat_model(
            model, model_provider=provider, max_retries=0,
            base_url=base_url, api_key=api_key,
        ).bind_tools(tools)
    else:
        os.environ["GROQ_API_KEY"] = api_key
        return init_chat_model(model, model_provider=provider, max_retries=0).bind_tools(tools)


def _throttled_invoke(llm, messages: list, api_key: str, model: str = ""):
    """Appelle llm.invoke() en respectant TPM + RPM Cerebras via fenêtre glissante."""
    # Estimate tokens for the outgoing request (~1 token per 4 chars)
    total_chars = sum(
        len(m.content) if isinstance(m.content, str) else 0
        for m in messages
    )
    estimated_tokens = max(500, total_chars // 4)

    wait = _tpm_wait(api_key, model, estimated_tokens)
    if wait > 0:
        logger.info("TPM/RPM throttle → attente %.1fs (modèle=%s)", wait, model)
        time.sleep(wait)

    result = llm.invoke(messages)

    # Record actual tokens used (or fall back to estimate)
    usage = getattr(result, "usage_metadata", None)
    actual = 0
    if usage:
        actual = (getattr(usage, "total_tokens", None) or
                  (getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)))
    _record_tokens(api_key, actual or estimated_tokens)

    return result


def _truncate_messages(messages: list) -> list:
    """Réduit le contexte pour rester sous la limite de tokens Groq.

    - Conserve tous les SystemMessage
    - Garde les _MAX_HISTORY_MESSAGES messages non-system les plus récents
    - Tronque le contenu de chaque message à _MAX_MSG_CHARS caractères
    """
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    other_msgs  = [m for m in messages if not isinstance(m, SystemMessage)]

    if len(other_msgs) > _MAX_HISTORY_MESSAGES:
        other_msgs = other_msgs[-_MAX_HISTORY_MESSAGES:]

    result = []
    for m in system_msgs + other_msgs:
        content = m.content if isinstance(m.content, str) else str(m.content)
        # Tool results tronqués plus agressivement — souvent très verbeux
        limit = _MAX_TOOL_RESULT_CHARS if isinstance(m, ToolMessage) else _MAX_MSG_CHARS
        if len(content) > limit:
            content = content[:limit] + "\n...[tronqué]"
            m = m.model_copy(update={"content": content})
        result.append(m)
    return result


def _is_tpm_exceeded(exc: Exception) -> bool:
    """413 TPM : la requête est trop grosse pour ce compte — changer de clé."""
    msg = str(exc)
    return "413" in msg or ("rate_limit_exceeded" in msg and "tokens per minute" in msg.lower())


def _is_rpm_exceeded(exc: Exception) -> bool:
    """429 RPM : trop de requêtes/minute — attendre sur la même clé."""
    msg = str(exc)
    return "429" in msg or "Too Many Requests" in msg


def _is_tpm_minute(exc: Exception) -> bool:
    """429 TPM/minute (Cerebras) : attendre 65s pour laisser la fenêtre se vider."""
    msg = str(exc)
    return "too_many_tokens_error" in msg or "token_quota_exceeded" in msg


def _is_cerebras(provider: str) -> bool:
    base = os.environ.get("OPENAI_API_BASE", "")
    return "cerebras" in base


def _inject_memory_context(messages: list, agent_name: str = "unknown") -> list:
    """Prepend a SystemMessage with relevant L3/L4 memories before the first HumanMessage.

    Extracts a query from the last HumanMessage or SystemMessage content,
    searches memory, and injects results as a SystemMessage — reducing the need
    to pass full conversation history.
    """
    try:
        from Memory.team_agent.memory import search_memory
        from langchain_core.messages import HumanMessage

        # Build query: dernier HumanMessage, sinon dernier SystemMessage non-prompt
        query = ""
        for m in reversed(messages):
            content = m.content if isinstance(m.content, str) else str(m.content)
            if content.strip() and "## Task" in content:
                # Extrait le contenu après "## Task"
                query = content.split("## Task")[-1].strip()[:300]
                break
            if not isinstance(m, SystemMessage) and content.strip():
                query = content[:300]
                break
        if not query and messages:
            query = (messages[0].content or "")[:300]

        if not query:
            return messages

        docs = search_memory(query, k=5)
        if not docs:
            return messages

        memory_lines = "\n".join(
            f"[{d.metadata.get('layer','?')}/{d.metadata.get('category','')}] {d.page_content}"
            for d in docs
        )

        # ── Trace: memory inject ──────────────────────────────────────────────
        try:
            tracer = get_tracer()
            layers = set(d.metadata.get("layer", "?") for d in docs)
            tracer.memory_op(agent_name, "inject", "+".join(sorted(layers)),
                             f"{len(docs)} docs injected",
                             query=query, results_count=len(docs))
        except Exception:
            pass

        memory_msg = SystemMessage(content=f"## Relevant memory (L3/L4)\n{memory_lines}")

        # Insert after system prompts, before the rest
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs  = [m for m in messages if not isinstance(m, SystemMessage)]
        return system_msgs + [memory_msg] + other_msgs

    except Exception as exc:
        logger.debug("Memory injection skipped: %s", exc)
        return messages


def run_tool_loop(
    model: str,
    provider: str,
    messages: list,
    tools: list,
    max_iterations: int = _MAX_TOOL_ITERATIONS,
    agent_name: str = "unknown",
) -> tuple[list[AIMessage | ToolMessage], list[str], dict]:
    """Invoke the LLM in a loop, executing tool calls until the model stops.

    Args:
        agent_name: Name of the calling agent — used for trace events.

    Returns:
        new_messages: AIMessage and ToolMessage produced during the loop
        files_written: paths passed to write_file calls
        token_usage: {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    """
    tracer = get_tracer()
    tracer.agent_start(agent_name)
    _loop_start = time.monotonic()

    tool_map = {t.name: t for t in tools}
    new_messages: list = []
    files_written: list[str] = []
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    current_messages = _inject_memory_context(list(messages), agent_name=agent_name)

    api_keys     = _get_api_keys()
    or_models    = _get_openrouter_models()   # non-vide = mode OpenRouter
    key_index    = 0
    model_index  = 0
    current_key  = api_keys[key_index] if api_keys else ""
    current_model = or_models[model_index] if or_models else model

    llm = _build_llm(current_model, provider, tools, current_key)

    for _iter in range(max_iterations):
        trimmed = _truncate_messages(current_messages)

        last_exc: Exception | None = None
        response = None

        # max 2 tours sur tous les modèles (OpenRouter) ou toutes les clés (Groq)
        n_slots = len(or_models) if or_models else (len(api_keys) or 1)
        for attempt in range(n_slots * 2):
            try:
                response = _throttled_invoke(llm, trimmed, current_key, current_model)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if _is_tpm_minute(exc) or (_is_rpm_exceeded(exc) and _is_cerebras(provider)):
                    # Cerebras 429 → vider la fenêtre glissante + attendre 65s
                    wait = 65
                    logger.info("Cerebras 429 → attente %ds + reset fenêtre tokens", wait)
                    # Marquer toute la fenêtre comme "pleine" pour forcer un wait long au prochain appel
                    tpm_limit = _CEREBRAS_TPM.get(current_model, 30_000)
                    _token_window[current_key] = [(time.monotonic(), tpm_limit)]
                    time.sleep(wait)
                    _last_call_time[current_key] = time.monotonic()
                elif _is_rpm_exceeded(exc):
                    if or_models:
                        # OpenRouter 429 → modèle suivant
                        model_index = (model_index + 1) % len(or_models)
                        current_model = or_models[model_index]
                        logger.warning(
                            "OpenRouter 429 → rotation modèle %d (%s)",
                            model_index + 1, current_model
                        )
                        llm = _build_llm(current_model, provider, tools, current_key)
                    else:
                        # Groq 429 RPM → attente courte, même clé
                        wait = 5
                        logger.info("RPM dépassé → attente %ds (même clé)", wait)
                        time.sleep(wait)
                elif _is_tpm_exceeded(exc) and api_keys and not or_models:
                    # Groq 413 → clé suivante
                    key_index = (key_index + 1) % len(api_keys)
                    current_key = api_keys[key_index]
                    logger.warning(
                        "TPM dépassé → rotation clé %d (%s...)",
                        key_index + 1, current_key[:8]
                    )
                    llm = _build_llm(current_model, provider, tools, current_key)
                else:
                    raise

        if last_exc is not None:
            tracer.error(agent_name, str(last_exc))
            raise last_exc
        if response is None:
            raise RuntimeError("LLM invoke returned None without exception")

        # Garantit que content n'est jamais None (évite MESSAGE_COERCION_FAILURE)
        if response.content is None:
            response = response.model_copy(update={"content": ""})

        # Accumule les tokens si le provider les retourne
        usage = getattr(response, "usage_metadata", None) or getattr(response, "response_metadata", {}).get("token_usage", {})
        iter_prompt     = 0
        iter_completion = 0
        iter_total      = 0
        if usage:
            iter_prompt     = getattr(usage, "input_tokens",  None) or usage.get("prompt_tokens",     0)
            iter_completion = getattr(usage, "output_tokens", None) or usage.get("completion_tokens", 0)
            iter_total      = getattr(usage, "total_tokens",  None) or usage.get("total_tokens",      0)
            token_usage["prompt_tokens"]     += iter_prompt
            token_usage["completion_tokens"] += iter_completion
            token_usage["total_tokens"]      += iter_total

        # ── Trace: LLM call ───────────────────────────────────────────────────
        tool_calls = getattr(response, "tool_calls", None) or []

        # Build prompt preview from last non-system messages
        prompt_preview = ""
        try:
            for m in reversed(trimmed):
                c = m.content if isinstance(m.content, str) else str(m.content)
                if c.strip() and not isinstance(m, SystemMessage):
                    prompt_preview = c[:500]
                    break
        except Exception:
            pass

        response_preview = ""
        try:
            rc = response.content if isinstance(response.content, str) else str(response.content)
            response_preview = rc[:500]
        except Exception:
            pass

        tracer.llm_call(
            agent_name, current_model,
            prompt_tokens=iter_prompt,
            completion_tokens=iter_completion,
            total_tokens=iter_total,
            iteration=_iter + 1,
            prompt_preview=prompt_preview,
        )
        tracer.llm_response(agent_name, has_tool_calls=bool(tool_calls), response_preview=response_preview)

        new_messages.append(response)
        current_messages.append(response)

        if not tool_calls:
            break

        for tc in tool_calls:
            tool_name = tc.get("name") if isinstance(tc, dict) else tc.name
            tool_args = tc.get("args", {}) if isinstance(tc, dict) else tc.args
            tool_id   = tc.get("id", "")  if isinstance(tc, dict) else tc.id

            if tool_name == "write_file":
                path = tool_args.get("path", "")
                if path and path not in files_written:
                    files_written.append(path)

            # ── Trace: tool call ──────────────────────────────────────────────
            _is_memory_tool = tool_name in ("remember", "recall", "commit_to_identity")
            if _is_memory_tool:
                layer = "L2+L3" if tool_name == "remember" else ("L4" if tool_name == "commit_to_identity" else "L3+L4")
                mem_content = str(tool_args.get("content", tool_args.get("query", "")))
                tracer.memory_op(agent_name, tool_name, layer,
                                 mem_content[:200],
                                 query=mem_content if tool_name == "recall" else "")
            else:
                tracer.tool_call(agent_name, tool_name, tool_args)

            tool_fn = tool_map.get(tool_name)
            if tool_fn is None:
                result = f"Error: tool '{tool_name}' not found."
                logger.warning("Tool not found: %s", tool_name)
            else:
                try:
                    result = tool_fn.invoke(tool_args)
                except Exception as exc:
                    result = f"Error running {tool_name}: {exc}"
                    logger.warning("Tool %s failed: %s", tool_name, exc)

            # ── Trace: tool result ────────────────────────────────────────────
            if not _is_memory_tool:
                tracer.tool_result(agent_name, tool_name, str(result))

            # tool_call_id ne peut pas être vide pour certains providers
            safe_id = tool_id or f"call_{tool_name}_{len(new_messages)}"
            tool_msg = ToolMessage(content=str(result) or "(no output)", tool_call_id=safe_id)
            new_messages.append(tool_msg)
            current_messages.append(tool_msg)

    if token_usage["total_tokens"] == 0 and token_usage["prompt_tokens"] > 0:
        token_usage["total_tokens"] = token_usage["prompt_tokens"] + token_usage["completion_tokens"]
    logger.info("Tokens utilisés — prompt:%d completion:%d total:%d",
                token_usage["prompt_tokens"], token_usage["completion_tokens"], token_usage["total_tokens"])

    _duration_ms = int((time.monotonic() - _loop_start) * 1000)
    tracer.agent_done(agent_name, _duration_ms)

    return new_messages, files_written, token_usage
