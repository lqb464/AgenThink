"""
Chat service for AgenThink — agent loop with planning, tools, reflection.

Loop: plan (light) → tool calls → observe → reflect/retry → deliver
with visible SSE progress and clean stop conditions.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from backend.agent.planner import light_plan, should_plan
from backend.agent.reflection import critique, should_reflect
from backend.core.client import get_llm
from backend.core.config import settings
from backend.core.observability import new_trace, timed_event
from backend.core.request_context import get_context
from backend.database.repository import (
    async_delete_session,
    async_get_session_messages_dicts,
    async_list_sessions,
    async_save_message,
)
from backend.memory.store import async_list_facts, format_memory
from backend.tools.executor import execute_tool
from backend.tools.schema_loader import get_tool_definitions_for_llm

logger = logging.getLogger(__name__)

# Fallbacks if settings missing older env
MAX_TOOL_ROUNDS = getattr(settings, "MAX_TOOL_ROUNDS", 10)
MAX_LLM_CALLS = getattr(settings, "MAX_LLM_CALLS_PER_TURN", 14)
MAX_REFLECTION_IN_LOOP = 1


# ---------------------------------------------------------------------------
# Session management via database layer
# ---------------------------------------------------------------------------


async def list_sessions(user_id: str | None = None) -> list[dict]:
    """Return a summary of sessions for a user."""
    return await async_list_sessions(user_id=user_id)


async def delete_session(session_id: str, user_id: str | None = None) -> bool:
    """Delete a session by ID (ownership enforced in repository)."""
    return await async_delete_session(session_id, user_id=user_id)


async def get_session_messages(session_id: str, user_id: str | None = None) -> list[dict]:
    """Return all messages for a session (for loading history in UI & agent loop)."""
    return await async_get_session_messages_dicts(session_id, user_id=user_id)


def _active_user_id(explicit: str | None = None) -> str | None:
    if explicit is not None:
        return explicit
    ctx = get_context()
    uid = ctx.user_id
    if uid in ("anonymous", "legacy", None):
        return None
    return uid


# ---------------------------------------------------------------------------
# Message building
# ---------------------------------------------------------------------------


async def _build_system_message(plan_steps: list[str] | None = None) -> dict:
    """Build the system message with persona, memory, language, and optional plan."""
    ctx = get_context()
    lang = (ctx.language or "vi").lower()
    if lang == "en":
        parts = [
            settings.SYSTEM_PROMPT,
            "\nLanguage: Respond in English unless the user asks otherwise.",
        ]
    else:
        parts = [
            settings.SYSTEM_PROMPT,
            "\nLanguage: Always respond in Vietnamese (Tiếng Việt) unless the user "
            "explicitly asks for another language.",
        ]

    facts = await async_list_facts(user_id=_active_user_id())
    if facts:
        memory_text = format_memory(facts)
        parts.append(f"\n{memory_text}")

    parts.append(
        "\nYou are an autonomous agent. For non-trivial goals: follow the plan, "
        "call concrete tools yourself (calculator, weather, web_search, wikipedia_lookup, "
        "arxiv_search, search_documents, summarize_documents, generate_document_report, "
        "vision, memory), "
        "observe results, then deliver a clear final answer. "
        "Prefer direct function calling over run_autonomous / run_multi_agent "
        "unless the user explicitly asks for those learning demos.\n"
        "\nTool routing (Hybrid RAG):\n"
        "- Prefer search_documents when the question is about uploaded / private docs "
        "(policies, PDFs in the Knowledge panel, project materials).\n"
        "- Prefer wikipedia_lookup for established public definitions/background.\n"
        "- Prefer arxiv_search for academic papers.\n"
        "- Prefer web_search for current events / public web facts not in RAG.\n"
        "- Use summarize_documents / generate_document_report for summaries or reports "
        "over uploaded sources.\n"
        "- When citing RAG, mention the source filenames from tool results.\n"
        "- For long reports/plans/code, structure with clear markdown headings so the "
        "UI can pin them as Artifacts."
    )

    if plan_steps:
        numbered = "\n".join(f"{i}. {step}" for i, step in enumerate(plan_steps, start=1))
        parts.append(
            f"\nCurrent turn plan (follow when useful; adapt if tools suggest otherwise):\n{numbered}"
        )

    return {"role": "system", "content": "\n".join(parts)}


def _build_user_message(text: str, images: list[bytes] | None = None) -> dict:
    """Build a user message, optionally with images (multimodal)."""
    if not images:
        return {"role": "user", "content": text}

    content = [{"type": "text", "text": text}]
    for img_bytes in images:
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            }
        )
    return {"role": "user", "content": content}


async def _build_messages(
    session_id: str,
    user_text: str,
    images: list[bytes] | None = None,
    plan_steps: list[str] | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Build the full message list for the LLM."""
    messages = [await _build_system_message(plan_steps)]
    history = await get_session_messages(session_id, user_id=_active_user_id(user_id))
    messages.extend(history)
    messages.append(_build_user_message(user_text, images))
    return messages


def _tool_call_fingerprint(name: str, arguments: dict) -> str:
    payload = json.dumps({"name": name, "arguments": arguments}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _assistant_tool_message(fc_id: str, fc_name: str, fc_args: dict) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": fc_id,
                "type": "function",
                "function": {
                    "name": fc_name,
                    "arguments": json.dumps(fc_args, ensure_ascii=False),
                },
            }
        ],
    }


def _tool_result_message(fc_id: str, content: str) -> dict:
    return {
        "role": "tool",
        "tool_call_id": fc_id,
        "content": content,
    }


# ---------------------------------------------------------------------------
# SSE events
# ---------------------------------------------------------------------------


@dataclass
class StreamEvent:
    """A single event in the SSE stream."""

    event: str  # text | tool_start | tool_result | plan | reflect | status | error | done
    data: str = ""

    def to_sse(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps({'content': self.data}, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


async def _persist_tool_exchange(
    session_id: str,
    fc_id: str,
    fc_name: str,
    fc_args: dict,
    result_text: str,
    user_id: str | None = None,
) -> None:
    uid = _active_user_id(user_id)
    await async_save_message(
        session_id,
        "assistant",
        None,
        tool_calls=[
            {
                "id": fc_id,
                "type": "function",
                "function": {
                    "name": fc_name,
                    "arguments": json.dumps(fc_args, ensure_ascii=False),
                },
            }
        ],
        user_id=uid,
    )
    await async_save_message(
        session_id,
        "tool",
        result_text,
        tool_call_id=fc_id,
        user_id=uid,
    )


# ---------------------------------------------------------------------------
# Non-streaming chat
# ---------------------------------------------------------------------------


async def chat_async(
    session_id: str,
    message: str,
    images: list[bytes] | None = None,
    user_id: str | None = None,
) -> tuple[str, dict]:
    """
    Full agent loop (non-streaming) — returns final text + trace metadata.
    """
    uid = _active_user_id(user_id)
    llm = get_llm()
    trace = new_trace()
    tools = get_tool_definitions_for_llm(check_health=True)
    tools_available = bool(tools)

    plan_steps: list[str] = []
    if settings.ENABLE_AGENT_PLANNING and should_plan(message, tools_available=tools_available):
        plan_steps = light_plan(message, use_llm=False)
        trace.add("plan", f"{len(plan_steps)} steps")

    messages = await _build_messages(session_id, message, images, plan_steps or None, user_id=uid)
    await async_save_message(
        session_id, "user", _build_user_message(message, images)["content"], user_id=uid
    )

    final_text = ""
    llm_calls = 0
    reflection_rounds = 0
    used_tools = False
    seen_fingerprints: set[str] = set()
    stop_reason = "goal_complete"

    with timed_event(trace, "agent_loop", message[:80]):
        for _round in range(MAX_TOOL_ROUNDS):
            if llm_calls >= MAX_LLM_CALLS:
                stop_reason = "budget"
                final_text = final_text or "⚠️ Đã hết ngân sách gọi LLM cho lượt này."
                break

            with timed_event(trace, "llm_call"):
                response = await llm.chat_with_tools(messages, tools)
            llm_calls += 1

            if response.has_function_calls:
                progress = False
                for fc in response.function_calls:
                    fp = _tool_call_fingerprint(fc.name, fc.arguments)
                    if fp in seen_fingerprints:
                        trace.add("no_progress", f"repeat {fc.name}")
                        continue
                    seen_fingerprints.add(fp)
                    progress = True

                    trace.add(
                        "tool_call",
                        f"{fc.name}({json.dumps(fc.arguments, ensure_ascii=False)[:100]})",
                    )
                    result = await execute_tool(fc.name, fc.arguments, images=images)
                    used_tools = True

                    assistant_msg = _assistant_tool_message(fc.call_id, fc.name, fc.arguments)
                    tool_msg = _tool_result_message(fc.call_id, result.to_llm_text())
                    messages.append(assistant_msg)
                    messages.append(tool_msg)
                    await _persist_tool_exchange(
                        session_id,
                        fc.call_id,
                        fc.name,
                        fc.arguments,
                        result.to_llm_text(),
                        user_id=uid,
                    )

                if not progress:
                    stop_reason = "no_progress"
                    final_text = (
                        final_text
                        or "⚠️ Agent dừng vì không có tiến triển mới (lặp lại cùng tool call)."
                    )
                    break
                continue

            draft = response.text or ""
            if (
                settings.ENABLE_AGENT_REFLECTION
                and should_reflect(message, used_tools=used_tools, draft=draft)
                and reflection_rounds < MAX_REFLECTION_IN_LOOP
            ):
                ok, feedback = critique(message, draft)
                llm_calls += 1  # critique uses an LLM call
                reflection_rounds += 1
                if not ok:
                    trace.add("reflect_fail", feedback[:120])
                    messages.append({"role": "assistant", "content": draft})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Phản hồi từ reviewer (FAIL). Hãy cải thiện câu trả lời "
                                f"dựa trên feedback sau (không cần gọi tool trừ khi thiếu dữ liệu):\n{feedback}"
                            ),
                        }
                    )
                    continue

            final_text = draft
            stop_reason = "goal_complete"
            break
        else:
            stop_reason = "max_rounds"
            final_text = final_text or "⚠️ Đã đạt giới hạn số vòng xử lý tool. Vui lòng thử lại."

    await async_save_message(session_id, "assistant", final_text, user_id=uid)

    trace.add("stop", stop_reason)
    trace.add_cost(settings.ESTIMATED_COST_PER_CALL_USD * max(1, llm_calls))
    summary = trace.summary()
    summary["cached"] = False
    summary["stop_reason"] = stop_reason
    summary["llm_calls"] = llm_calls
    return final_text, summary


# ---------------------------------------------------------------------------
# Streaming chat (SSE)
# ---------------------------------------------------------------------------


async def chat_stream(
    session_id: str,
    message: str,
    images: list[bytes] | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Streaming agent loop — yields SSE events for plan / tools / reflect / text.
    """
    uid = _active_user_id(user_id)
    llm = get_llm()
    tools = get_tool_definitions_for_llm(check_health=True)
    tools_available = bool(tools)

    plan_steps: list[str] = []
    if settings.ENABLE_AGENT_PLANNING and should_plan(message, tools_available=tools_available):
        plan_steps = light_plan(message, use_llm=False)
        yield StreamEvent(
            event="plan",
            data=json.dumps({"steps": plan_steps}, ensure_ascii=False),
        )

    messages = await _build_messages(
        session_id, message, images, plan_steps or None, user_id=uid
    )
    user_content = _build_user_message(message, images)["content"]
    await async_save_message(session_id, "user", user_content, user_id=uid)

    full_text = ""
    llm_calls = 0
    reflection_rounds = 0
    used_tools = False
    seen_fingerprints: set[str] = set()
    stop_reason = "goal_complete"
    cancelled = False

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            if llm_calls >= MAX_LLM_CALLS:
                stop_reason = "budget"
                yield StreamEvent(
                    event="status",
                    data=json.dumps({"stop_reason": stop_reason}, ensure_ascii=False),
                )
                if not full_text:
                    yield StreamEvent(
                        event="error",
                        data="Đã hết ngân sách gọi LLM cho lượt này.",
                    )
                break

            text_chunks: list[str] = []
            function_calls: list[dict] = []
            # Buffer text when reflection may rewrite the draft (avoids flashing FAIL text)
            may_reflect = (
                settings.ENABLE_AGENT_REFLECTION
                and reflection_rounds < MAX_REFLECTION_IN_LOOP
                and (used_tools or len(message.strip()) >= 60)
            )

            async for chunk in llm.chat_stream(messages, tools):
                if chunk["type"] == "text":
                    text_chunks.append(chunk["content"])
                    if not may_reflect:
                        yield StreamEvent(event="text", data=chunk["content"])
                elif chunk["type"] == "function_call":
                    function_calls.append(chunk)
                elif chunk["type"] == "done":
                    pass

            llm_calls += 1

            if function_calls:
                progress = False
                for fc in function_calls:
                    fc_name = fc["name"]
                    fc_args = fc["arguments"]
                    fc_id = fc.get("call_id") or f"call_{fc_name}_{_round}"

                    fp = _tool_call_fingerprint(fc_name, fc_args)
                    if fp in seen_fingerprints:
                        yield StreamEvent(
                            event="status",
                            data=json.dumps(
                                {"stop_reason": "no_progress", "tool": fc_name},
                                ensure_ascii=False,
                            ),
                        )
                        continue
                    seen_fingerprints.add(fp)
                    progress = True

                    yield StreamEvent(
                        event="tool_start",
                        data=json.dumps(
                            {"tool": fc_name, "arguments": fc_args},
                            ensure_ascii=False,
                        ),
                    )

                    result = await execute_tool(fc_name, fc_args, images=images)
                    used_tools = True

                    yield StreamEvent(
                        event="tool_result",
                        data=json.dumps(
                            result.to_sse_dict(arguments=fc_args, text_limit=800),
                            ensure_ascii=False,
                        ),
                    )

                    assistant_msg = _assistant_tool_message(fc_id, fc_name, fc_args)
                    tool_msg = _tool_result_message(fc_id, result.to_llm_text())
                    messages.append(assistant_msg)
                    messages.append(tool_msg)
                    await _persist_tool_exchange(
                        session_id,
                        fc_id,
                        fc_name,
                        fc_args,
                        result.to_llm_text(),
                        user_id=uid,
                    )

                if not progress:
                    stop_reason = "no_progress"
                    yield StreamEvent(
                        event="error",
                        data="Agent dừng vì không có tiến triển mới (lặp lại cùng tool call).",
                    )
                    break
                continue

            draft = "".join(text_chunks)

            if (
                settings.ENABLE_AGENT_REFLECTION
                and should_reflect(message, used_tools=used_tools, draft=draft)
                and reflection_rounds < MAX_REFLECTION_IN_LOOP
            ):
                yield StreamEvent(
                    event="reflect",
                    data=json.dumps({"status": "critiquing"}, ensure_ascii=False),
                )
                ok, feedback = await asyncio.to_thread(critique, message, draft)
                llm_calls += 1
                reflection_rounds += 1

                if not ok:
                    yield StreamEvent(
                        event="reflect",
                        data=json.dumps(
                            {"status": "retry", "feedback": feedback[:300]},
                            ensure_ascii=False,
                        ),
                    )
                    messages.append({"role": "assistant", "content": draft})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Phản hồi từ reviewer (FAIL). Hãy cải thiện câu trả lời "
                                f"dựa trên feedback sau (không cần gọi tool trừ khi thiếu dữ liệu):\n{feedback}"
                            ),
                        }
                    )
                    continue

                yield StreamEvent(
                    event="reflect",
                    data=json.dumps({"status": "pass"}, ensure_ascii=False),
                )

            # Flush buffered (or already-streamed) final answer
            if may_reflect and draft:
                yield StreamEvent(event="text", data=draft)
            full_text = draft
            stop_reason = "goal_complete"
            break
        else:
            stop_reason = "max_rounds"
            yield StreamEvent(event="error", data="Đã đạt giới hạn số vòng xử lý tool.")

    except asyncio.CancelledError:
        cancelled = True
        stop_reason = "cancelled"
        raise
    except Exception as exc:
        logger.error("Stream error: %s", exc)
        yield StreamEvent(event="error", data=str(exc))
        stop_reason = "error"
    finally:
        try:
            if full_text:
                await async_save_message(session_id, "assistant", full_text, user_id=uid)
            elif used_tools:
                await async_save_message(
                    session_id,
                    "assistant",
                    "⚠️ Đã dừng theo yêu cầu người dùng." if cancelled else "⚠️ Phiên stream kết thúc sớm.",
                    user_id=uid,
                )
        except Exception as save_exc:
            logger.error("Failed to persist assistant message: %s", save_exc)

    if not cancelled:
        yield StreamEvent(
            event="status",
            data=json.dumps({"stop_reason": stop_reason}, ensure_ascii=False),
        )
        yield StreamEvent(event="done", data="")


# ---------------------------------------------------------------------------
# Backward-compatible sync API (used by old agent modules)
# ---------------------------------------------------------------------------


def chat(message: str) -> str:
    """Synchronous chat — backward compatible with existing code."""
    import asyncio as _asyncio

    try:
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return llm.chat(f"System: {settings.SYSTEM_PROMPT}\nUser: {message}")

    return _asyncio.run(_simple_chat(message))


async def _simple_chat(message: str) -> str:
    result, _ = await chat_async("default", message)
    return result
