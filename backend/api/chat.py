"""
Chat API routes for AgenThink.

- POST /api/chat — non-streaming chat
- POST /api/chat/stream — SSE streaming chat with file upload
- GET /api/sessions — list sessions
- GET /api/sessions/{session_id} — get session messages
- DELETE /api/sessions/{session_id} — delete session
- GET /api/health — health check with service statuses
"""

import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.core.auth_deps import AuthUser, require_user
from backend.core.config import settings
from backend.core.rate_limit import RateLimiter, rate_limiter
from backend.core.request_context import RequestContext, set_context
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import (
    chat_async,
    chat_stream,
    delete_session,
    get_session_messages,
    list_sessions,
)
from backend.tools.schema_loader import get_service_statuses

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_rate_limit(client_key: str = "global") -> None:
    limiter: RateLimiter = rate_limiter
    limiter.max_calls = settings.RATE_LIMIT_MAX_CALLS
    limiter.period = settings.RATE_LIMIT_WINDOW_SECONDS
    if not limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _apply_prefs(
    user: AuthUser,
    language: str = "vi",
    llm_provider: str | None = None,
    llm_model: str | None = None,
    openai_base_url: str | None = None,
) -> None:
    lang = (language or "vi").strip().lower()
    if lang not in ("vi", "en"):
        lang = "vi"
    set_context(
        RequestContext(
            user_id=user.id if user.id not in ("anonymous",) else None,
            email=user.email,
            rag_project_id=user.rag_project_id,
            language=lang,
            llm_provider=(llm_provider or "").strip() or None,
            llm_model=(llm_model or "").strip() or None,
            openai_base_url=(openai_base_url or "").strip() or None,
        )
    )


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: AuthUser = Depends(require_user),
):
    """Non-streaming chat endpoint (backward compatible)."""
    _check_rate_limit(user.id)
    _apply_prefs(
        user,
        language=request.language or "vi",
        llm_provider=request.llm_provider,
        llm_model=request.llm_model,
        openai_base_url=request.openai_base_url,
    )

    session_id = request.session_id or str(uuid.uuid4())[:8]
    uid = user.id if user.id not in ("anonymous",) else None

    try:
        answer, meta = await chat_async(session_id, request.message, user_id=uid)
        return ChatResponse(
            response=answer,
            session_id=session_id,
            request_id=meta.get("request_id"),
            cached=meta.get("cached", False),
            estimated_cost_usd=meta.get("estimated_cost_usd"),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Session access denied")
    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc)
        return ChatResponse(
            response=f"⚠️ [Lỗi dịch vụ LLM] {exc!s}. Vui lòng thử lại sau.",
            session_id=session_id,
            cached=False,
            estimated_cost_usd=0.0,
        )


@router.post("/api/chat/stream")
async def chat_stream_endpoint(
    message: str = Form(...),
    session_id: str = Form(default=""),
    language: str = Form(default="vi"),
    llm_provider: str = Form(default=""),
    llm_model: str = Form(default=""),
    openai_base_url: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
    user: AuthUser = Depends(require_user),
):
    """
    SSE streaming chat endpoint with multimodal support.

    Accepts form data with optional file uploads (images).
    Optional prefs: language, llm_provider, llm_model, openai_base_url.
    """
    _check_rate_limit(user.id)
    _apply_prefs(user, language, llm_provider, llm_model, openai_base_url)

    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    uid = user.id if user.id not in ("anonymous",) else None

    images: list[bytes] = []
    for file in files:
        content = await file.read()
        if content:
            images.append(content)

    async def event_generator():
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        try:
            async for event in chat_stream(session_id, message, images or None, user_id=uid):
                yield event.to_sse()
        except PermissionError:
            yield f"event: error\ndata: {json.dumps({'content': 'Session access denied'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Session endpoints
# ---------------------------------------------------------------------------


@router.get("/api/sessions")
async def list_sessions_endpoint(user: AuthUser = Depends(require_user)):
    """List chat sessions for the current user."""
    uid = user.id if user.id not in ("anonymous",) else None
    return {"sessions": await list_sessions(user_id=uid)}


@router.get("/api/sessions/{session_id}")
async def get_session_endpoint(session_id: str, user: AuthUser = Depends(require_user)):
    """Get all messages for a specific session (ownership enforced)."""
    from backend.database.connection import async_session_maker
    from backend.database.models import SessionModel
    from backend.database.repository import async_assert_session_access
    from sqlalchemy import select

    uid = user.id if user.id not in ("anonymous",) else None
    async with async_session_maker() as db:
        row = (
            await db.execute(select(SessionModel).where(SessionModel.id == session_id))
        ).scalar_one_or_none()
        if row and not await async_assert_session_access(session_id, uid):
            raise HTTPException(status_code=404, detail="Session not found")

    messages = await get_session_messages(session_id, user_id=uid)
    return {"session_id": session_id, "messages": messages}


@router.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str, user: AuthUser = Depends(require_user)):
    """Delete a chat session owned by the current user."""
    uid = user.id if user.id not in ("anonymous",) else None
    if await delete_session(session_id, user_id=uid):
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


# ---------------------------------------------------------------------------
# Health / model profiles (public)
# ---------------------------------------------------------------------------


@router.get("/api/health")
async def health_check():
    """Enhanced health check with service status overview."""
    services = get_service_statuses()
    return {
        "status": "ok",
        "agent": "AgenThink",
        "version": "1.0.0-hybrid",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else settings.OPENAI_MODEL,
        "gemini_key_count": len(settings.get_gemini_api_keys()) if settings.LLM_PROVIDER == "gemini" else 0,
        "auth_required": settings.AUTH_REQUIRED,
        "services": services,
        "features": {
            "streaming": settings.ENABLE_STREAMING,
            "multimodal": settings.ENABLE_MULTIMODAL,
            "planning": settings.ENABLE_AGENT_PLANNING,
            "reflection": settings.ENABLE_AGENT_REFLECTION,
            "artifacts": True,
            "i18n": True,
            "model_picker": True,
        },
        "model_profiles": {
            "gemini": {"provider": "gemini", "model": settings.GEMINI_MODEL},
            "openai": {
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "base_url": settings.OPENAI_BASE_URL,
            },
            "local": {
                "provider": "local",
                "model": settings.LOCAL_OPENAI_MODEL,
                "base_url": settings.LOCAL_OPENAI_BASE_URL,
                "presets": {
                    "ollama": settings.LOCAL_OPENAI_BASE_URL,
                    "vllm": settings.VLLM_OPENAI_BASE_URL,
                },
            },
        },
    }
