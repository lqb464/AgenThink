import re

from app.agent.autonomous import run_autonomous
from app.agent.multi_agent import run_multi_agent
from app.agent.planner import match_plan_request, run_planning
from app.agent.reflection import reflect_until_good
from app.agent.workflow import match_workflow, run_workflow
from app.core.cache import response_cache
from app.core.client import llm
from app.core.config import settings
from app.core.observability import new_trace, timed_event
from app.core.retry import with_retry
from app.memory import extract_and_store, format_memory
from app.rag import format_context, retrieve
from app.tools import run_tool


conversation_store: list[dict[str, str]] = []

_AUTONOMOUS_RE = re.compile(
    r"^(?:Goal|Mục tiêu)\s*[:\-]\s*(.+)$",
    flags=re.IGNORECASE,
)
_MULTI_AGENT_RE = re.compile(
    r"^(?:Team|Multi-agent|Nhóm agent)\s*[:\-]\s*(.+)$",
    flags=re.IGNORECASE,
)


def _build_prompt(message: str, rag_context: str = "", memory_context: str = "") -> str:
    prompt_lines = [f"System: {settings.SYSTEM_PROMPT}"]

    if memory_context:
        prompt_lines.append(memory_context)

    if rag_context:
        prompt_lines.append(rag_context)
        prompt_lines.append(
            "Answer using the retrieved documents when relevant. "
            "If the documents do not contain the answer, say you do not know."
        )

    if conversation_store:
        history_lines = [
            f"{entry['role'].capitalize()}: {entry['content']}"
            for entry in conversation_store
        ]
        prompt_lines.append("Conversation history:")
        prompt_lines.extend(history_lines)

    prompt_lines.append(f"User: {message}")
    return "\n".join(prompt_lines)


def _generate_llm_answer(message: str) -> str:
    docs = retrieve(message, top_k=2)
    rag_context = format_context(docs)
    memory_context = format_memory()
    prompt = _build_prompt(
        message,
        rag_context=rag_context,
        memory_context=memory_context,
    )
    draft = with_retry(lambda: llm.chat(prompt), retries=2)
    return reflect_until_good(message, draft)


def chat_with_trace(message: str) -> tuple[str, dict]:
    """Production entrypoint: answer + observability metadata."""
    trace = new_trace()

    if settings.CACHE_ENABLED:
        cached = response_cache.get(message)
        if cached is not None:
            trace.add("cache_hit", "served from LRU cache")
            return cached, {**trace.summary(), "cached": True}

    with timed_event(trace, "route", message[:80]):
        memory_ack = extract_and_store(message)
        if memory_ack is not None:
            response = memory_ack
        else:
            workflow_name = match_workflow(message)
            multi_match = _MULTI_AGENT_RE.match(message.strip())
            autonomous_match = _AUTONOMOUS_RE.match(message.strip())
            goal = match_plan_request(message)
            tool_hit = run_tool(message)

            if workflow_name is not None:
                trace.add("workflow", workflow_name)
                response = run_workflow(workflow_name)
            elif multi_match:
                trace.add("multi_agent", multi_match.group(1).strip()[:80])
                response = run_multi_agent(multi_match.group(1).strip())
            elif autonomous_match:
                trace.add("autonomous", autonomous_match.group(1).strip()[:80])
                response = run_autonomous(autonomous_match.group(1).strip())
            elif goal is not None:
                trace.add("planning", goal[:80])
                response = run_planning(goal)
            elif tool_hit is not None:
                tool_name, tool_result = tool_hit
                trace.add("tool", tool_name)
                response = tool_result
            else:
                with timed_event(trace, "llm_with_reflection"):
                    response = _generate_llm_answer(message)
                trace.add_cost(settings.ESTIMATED_COST_PER_CALL_USD)

    conversation_store.append({"role": "user", "content": message})
    conversation_store.append({"role": "assistant", "content": response})

    if settings.CACHE_ENABLED:
        response_cache.set(message, response)

    summary = trace.summary()
    summary["cached"] = False
    return response, summary


def chat(message: str) -> str:
    answer, _meta = chat_with_trace(message)
    return answer
