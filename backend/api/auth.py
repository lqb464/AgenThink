"""Auth API — register / login / refresh / me."""

from __future__ import annotations

import logging

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.core.auth_deps import AuthUser, require_user
from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.database.repository import (
    async_create_user,
    async_get_user_by_email,
    async_get_user_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _valid_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
        raise ValueError("Invalid email")
    return v


class RegisterBody(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def email_ok(cls, v: str) -> str:
        return _valid_email(v)


class LoginBody(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_ok(cls, v: str) -> str:
        return _valid_email(v)


class RefreshBody(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


async def _ensure_rag_project(project_id: str, name: str, owner_id: str | None = None) -> None:
    """Best-effort create local RAG project dirs for new user."""
    try:
        from backend.rag import engine as rag_engine

        rag_engine.ensure_project(project_id, name=name)
    except Exception as exc:
        logger.info("Local RAG project ensure soft-fail for %s: %s", project_id, exc)


def _tokens_for(user: dict) -> TokenResponse:
    access = create_access_token(user["id"], user["email"], {"rag_project_id": user["rag_project_id"]})
    refresh = create_refresh_token(user["id"], user["email"])
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user={
            "id": user["id"],
            "email": user["email"],
            "rag_project_id": user["rag_project_id"],
        },
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterBody):
    if not settings.JWT_SECRET or settings.JWT_SECRET.startswith("change-me"):
        logger.warning("JWT_SECRET is a placeholder — set a strong secret for production")

    email = str(body.email).strip().lower()
    existing = await async_get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    try:
        user = await async_create_user(email, hash_password(body.password))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    await _ensure_rag_project(user["rag_project_id"], f"AgenThink · {email}", owner_id=user["id"])
    return _tokens_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody):
    email = str(body.email).strip().lower()
    user = await async_get_user_by_email(email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshBody):
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await async_get_user_by_id(str(payload.get("sub") or ""))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _tokens_for(user)


@router.get("/me")
async def me(user: AuthUser = Depends(require_user)):
    if user.id in ("anonymous", "legacy"):
        return {
            "id": user.id,
            "email": user.email,
            "rag_project_id": user.rag_project_id,
            "auth_mode": user.id,
        }
    row = await async_get_user_by_id(user.id)
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return {
        "id": row["id"],
        "email": row["email"],
        "rag_project_id": row["rag_project_id"],
        "auth_mode": "jwt",
    }
