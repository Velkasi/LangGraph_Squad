# ── tool_loop.py — Shared tool execution loop for all agent nodes ────

from __future__ import annotations

import logging
import os
import time

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 30
_MAX_MSG_CHARS = 16_000
_MAX_HISTORY_MESSAGES = 6

_last_call_time: dict[str, float] = {}  # clé → timestamp dernier appel
_MIN_CALL_INTERVAL = 0.5  # anti-burst minimal entre deux appels sur la même clé


def _get_groq_keys() -> list[str]:
    try:
        from Config.team_agent.config import _GROQ_KEYS
        return list(_GROQ_KEYS)
    except Exception:
        k = os.environ.get("GROQ_API_KEY", "")
        return [k] if k else []


def _build_llm(model: str, provider: str, tools: list, api_key: str):
    """Crée un LLM frais avec la clé donnée.

    max_retries=0 désactive le retry interne de LangChain/httpx
    pour que notre boucle de rotation gère les 429/413.
    """
    os.environ["GROQ_API_KEY"] = api_key
    return init_chat_model(model, model_provider=provider, max_retries=0).bind_tools(tools)


def _throttled_invoke(llm, messages: list, api_key: str):
    """Appelle llm.invoke() en respectant _MIN_CALL_INTERVAL par clé."""
    now = time.monotonic()
    last = _last_call_time.get(api_key, 0.0)
    wait = _MIN_CALL_INTERVAL - (now - last)
    if wait > 0:
        time.sleep(wait)
    result = llm.invoke(messages)
    _last_call_time[api_key] = time.monotonic()
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
        if len(content) > _MAX_MSG_CHARS:
            content = content[:_MAX_MSG_CHARS] + "\n...[tronqué]"
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


def _inject_memory_context(messages: list) -> list:
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
) -> tuple[list[AIMessage | ToolMessage], list[str]]:
    """Invoke the LLM in a loop, executing tool calls until the model stops.

    - Injecte automatiquement les souvenirs L3/L4 pertinents avant le premier appel.
    - Tronque le contexte pour rester sous la limite de tokens Groq.
    - Retry sur la clé suivante en cas d'erreur 413/429.

    Returns:
        new_messages: AIMessage and ToolMessage produced during the loop
        files_written: paths passed to write_file calls
    """
    tool_map = {t.name: t for t in tools}
    new_messages: list = []
    files_written: list[str] = []

    # Injecter les mémoires pertinentes pour réduire le contexte nécessaire
    current_messages = _inject_memory_context(list(messages))

    groq_keys = _get_groq_keys()
    key_index = 0

    # LLM initial
    llm = _build_llm(model, provider, tools, groq_keys[key_index] if groq_keys else "")

    for _ in range(max_iterations):
        trimmed = _truncate_messages(current_messages)

        # 413 TPM → rotation vers clé suivante
        # 429 RPM → attente courte sur la même clé
        # autres erreurs → remonte immédiatement
        last_exc: Exception | None = None
        response = None
        current_key = groq_keys[key_index] if groq_keys else ""

        for attempt in range((len(groq_keys) or 1) * 2):  # max 2 tours complets
            try:
                response = _throttled_invoke(llm, trimmed, current_key)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if _is_tpm_exceeded(exc) and groq_keys:
                    # Requête trop lourde pour ce compte → clé suivante
                    key_index = (key_index + 1) % len(groq_keys)
                    current_key = groq_keys[key_index]
                    logger.warning(
                        "TPM dépassé → rotation clé %d (%s...)",
                        key_index + 1, current_key[:8]
                    )
                    llm = _build_llm(model, provider, tools, current_key)
                elif _is_rpm_exceeded(exc):
                    # Trop de requêtes/min → attente courte, même clé
                    wait = 5
                    logger.info("RPM dépassé → attente %ds (même clé)", wait)
                    time.sleep(wait)
                else:
                    raise  # erreur non-rate-limit → remonte immédiatement

        if last_exc is not None:
            raise last_exc
        if response is None:
            raise RuntimeError("LLM invoke returned None without exception")

        # Garantit que content n'est jamais None (évite MESSAGE_COERCION_FAILURE)
        if response.content is None:
            response = response.model_copy(update={"content": ""})

        new_messages.append(response)
        current_messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
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

            # tool_call_id ne peut pas être vide pour certains providers
            safe_id = tool_id or f"call_{tool_name}_{len(new_messages)}"
            tool_msg = ToolMessage(content=str(result) or "(no output)", tool_call_id=safe_id)
            new_messages.append(tool_msg)
            current_messages.append(tool_msg)

    return new_messages, files_written
