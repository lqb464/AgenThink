"""Password hashing (bcrypt) and JWT access/refresh tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, email: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": _now() + timedelta(minutes=settings.JWT_ACCESS_MINUTES),
        "iat": _now(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "exp": _now() + timedelta(days=settings.JWT_REFRESH_DAYS),
        "iat": _now(),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected {expected_type} token")
    return payload


def fingerprint_token(token: str) -> str:
    """Non-reversible short id for logs (never log raw JWT)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
