"""Per-request context (user + RAG project + chat prefs) for tools/services."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    user_id: str | None = None
    email: str | None = None
    rag_project_id: str | None = None
    language: str = "vi"  # vi | en
    llm_provider: str | None = None  # gemini | openai | local
    llm_model: str | None = None
    openai_base_url: str | None = None


_ctx: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())


def get_context() -> RequestContext:
    return _ctx.get()


def set_context(ctx: RequestContext):
    return _ctx.set(ctx)


def reset_context(token) -> None:
    _ctx.reset(token)


def rag_project_or_default() -> str:
    from backend.core.config import settings

    ctx = get_context()
    return (ctx.rag_project_id or settings.RAG_PROJECT_ID or "agentthink_default").strip()
