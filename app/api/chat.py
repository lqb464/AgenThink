from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.core.rate_limit import RateLimiter, rate_limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_with_trace


router = APIRouter()


def _check_auth(authorization: str | None) -> None:
    if not settings.API_TOKEN:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def _check_rate_limit(client_key: str = "global") -> None:
    limiter: RateLimiter = rate_limiter
    limiter.max_calls = settings.RATE_LIMIT_MAX_CALLS
    limiter.period = settings.RATE_LIMIT_WINDOW_SECONDS
    if not limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
):
    _check_auth(authorization)
    _check_rate_limit()

    answer, meta = chat_with_trace(request.message)

    return ChatResponse(
        response=answer,
        request_id=meta.get("request_id"),
        cached=bool(meta.get("cached")),
        estimated_cost_usd=meta.get("estimated_cost_usd"),
    )
