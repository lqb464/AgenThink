"""FastAPI auth dependencies — JWT multi-user."""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException

from backend.core.config import settings
from backend.core.request_context import RequestContext, set_context
from backend.core.security import constant_time_eq, decode_token
from backend.database.repository import async_get_user_by_id


@dataclass
class AuthUser:
    id: str
    email: str
    rag_project_id: str


async def _load_user(user_id: str) -> AuthUser:
    row = await async_get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthUser(
        id=row["id"],
        email=row["email"],
        rag_project_id=row["rag_project_id"],
    )


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
) -> AuthUser | None:
    """Resolve JWT user, or legacy API_TOKEN, or None when auth not required."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        # Legacy single shared API_TOKEN
        if settings.API_TOKEN and constant_time_eq(token, settings.API_TOKEN):
            return AuthUser(
                id="legacy",
                email="legacy@local",
                rag_project_id=settings.RAG_PROJECT_ID,
            )
        if settings.JWT_SECRET:
            try:
                payload = decode_token(token, expected_type="access")
                user_id = str(payload.get("sub") or "")
                if not user_id:
                    raise HTTPException(status_code=401, detail="Invalid token")
                return await _load_user(user_id)
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
    return None


async def require_user(
    authorization: str | None = Header(default=None),
) -> AuthUser:
    user = await get_current_user_optional(authorization)
    if user:
        set_context(
            RequestContext(
                user_id=user.id,
                email=user.email,
                rag_project_id=user.rag_project_id,
            )
        )
        return user

    if not settings.AUTH_REQUIRED:
        # Anonymous single-tenant (AUTH_REQUIRED=false)
        set_context(
            RequestContext(
                user_id=None,
                email=None,
                rag_project_id=settings.RAG_PROJECT_ID,
            )
        )
        return AuthUser(
            id="anonymous",
            email="anonymous@local",
            rag_project_id=settings.RAG_PROJECT_ID,
        )

    raise HTTPException(status_code=401, detail="Authentication required")


async def require_user_dep(user: AuthUser = Depends(require_user)) -> AuthUser:
    return user
