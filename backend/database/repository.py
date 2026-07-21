"""
Repository functions for database CRUD operations.
Supports both async execution and sync wrapper methods for legacy code.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import async_session_maker
from backend.database.models import MemoryFactModel, MessageModel, SessionModel, UserModel

logger = logging.getLogger(__name__)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def make_rag_project_id(user_id: str) -> str:
    """Stable per-user local RAG project id (safe for path/hash)."""
    short = re.sub(r"[^a-zA-Z0-9_]", "", user_id.replace("-", ""))[:12]
    return f"user_{short or uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def async_create_user(email: str, password_hash: str, rag_project_id: str | None = None) -> dict:
    email_n = _normalize_email(email)
    user_id = str(uuid.uuid4())
    pid = rag_project_id or make_rag_project_id(user_id)
    async with async_session_maker() as session:
        existing = (
            await session.execute(select(UserModel).where(UserModel.email == email_n))
        ).scalar_one_or_none()
        if existing:
            raise ValueError("Email already registered")
        user = UserModel(
            id=user_id,
            email=email_n,
            password_hash=password_hash,
            rag_project_id=pid,
        )
        session.add(user)
        await session.commit()
        return {
            "id": user.id,
            "email": user.email,
            "rag_project_id": user.rag_project_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


async def async_get_user_by_email(email: str) -> dict | None:
    email_n = _normalize_email(email)
    async with async_session_maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.email == email_n))
        ).scalar_one_or_none()
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "rag_project_id": user.rag_project_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


async def async_get_user_by_id(user_id: str) -> dict | None:
    async with async_session_maker() as session:
        user = (
            await session.execute(select(UserModel).where(UserModel.id == user_id))
        ).scalar_one_or_none()
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "rag_project_id": user.rag_project_id,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }


# ---------------------------------------------------------------------------
# Memory repository (Facts) — scoped by user_id when provided
# ---------------------------------------------------------------------------

async def async_add_fact(fact: str, user_id: str | None = None) -> None:
    fact = fact.strip()
    if not fact:
        return
    async with async_session_maker() as session:
        try:
            stmt = select(MemoryFactModel).where(MemoryFactModel.fact == fact)
            if user_id:
                stmt = stmt.where(MemoryFactModel.user_id == user_id)
            else:
                stmt = stmt.where(MemoryFactModel.user_id.is_(None))
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                memory = MemoryFactModel(fact=fact, user_id=user_id)
                session.add(memory)
                await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.error("Error adding memory fact: %s", exc)


async def async_list_facts(user_id: str | None = None) -> list[str]:
    async with async_session_maker() as session:
        stmt = select(MemoryFactModel.fact).order_by(MemoryFactModel.id.asc())
        if user_id:
            stmt = stmt.where(MemoryFactModel.user_id == user_id)
        else:
            stmt = stmt.where(MemoryFactModel.user_id.is_(None))
        result = await session.execute(stmt)
        return [row[0] for row in result.fetchall()]


async def async_clear_facts(user_id: str | None = None) -> None:
    async with async_session_maker() as session:
        stmt = delete(MemoryFactModel)
        if user_id:
            stmt = stmt.where(MemoryFactModel.user_id == user_id)
        else:
            stmt = stmt.where(MemoryFactModel.user_id.is_(None))
        await session.execute(stmt)
        await session.commit()


# Sync helpers for existing non-async code (tools/handlers)
def _run_sync(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    return asyncio.run(coro)


def add_fact_sync(fact: str, user_id: str | None = None) -> None:
    _run_sync(async_add_fact(fact, user_id=user_id))


def list_facts_sync(user_id: str | None = None) -> list[str]:
    return _run_sync(async_list_facts(user_id=user_id))


def clear_facts_sync(user_id: str | None = None) -> None:
    _run_sync(async_clear_facts(user_id=user_id))


# ---------------------------------------------------------------------------
# Sessions & Messages repository
# ---------------------------------------------------------------------------

def _session_user_filter(stmt, user_id: str | None):
    if user_id and user_id not in ("anonymous", "legacy"):
        return stmt.where(SessionModel.user_id == user_id)
    if user_id == "legacy":
        return stmt  # shared token sees all (admin-like legacy)
    # anonymous / None: only unowned sessions
    return stmt.where(SessionModel.user_id.is_(None))


async def async_get_or_create_session(
    session_id: str,
    title: str = "New Chat",
    user_id: str | None = None,
) -> SessionModel:
    uid = user_id if user_id not in ("anonymous", "legacy", None) else None
    async with async_session_maker() as session:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if not s:
            s = SessionModel(id=session_id, title=title, user_id=uid)
            session.add(s)
            await session.commit()
            await session.refresh(s)
            return s
        # Ownership check on existing
        if uid and s.user_id and s.user_id != uid:
            raise PermissionError("Session belongs to another user")
        if uid and not s.user_id:
            s.user_id = uid
            await session.commit()
            await session.refresh(s)
        return s


async def async_list_sessions(user_id: str | None = None) -> list[dict]:
    async with async_session_maker() as session:
        stmt = select(SessionModel).order_by(SessionModel.updated_at.desc())
        stmt = _session_user_filter(stmt, user_id)
        result = await session.execute(stmt)
        sessions = result.scalars().all()

        output = []
        for s in sessions:
            msg_stmt = select(MessageModel).where(MessageModel.session_id == s.id)
            msgs = (await session.execute(msg_stmt)).scalars().all()
            output.append({
                "id": s.id,
                "title": s.title,
                "message_count": len(msgs),
                "updated_at": s.updated_at.isoformat(),
                "user_id": s.user_id,
            })
        return output


async def async_delete_session(session_id: str, user_id: str | None = None) -> bool:
    async with async_session_maker() as session:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        stmt = _session_user_filter(stmt, user_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if not s:
            return False
        await session.delete(s)
        await session.commit()
        return True


async def async_assert_session_access(session_id: str, user_id: str | None = None) -> bool:
    """Return True if session exists and belongs to user (or is unowned for anon)."""
    async with async_session_maker() as session:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if not s:
            return False
        if user_id and user_id not in ("anonymous", "legacy"):
            return s.user_id == user_id
        if user_id == "legacy":
            return True
        return s.user_id is None


async def async_save_message(
    session_id: str,
    role: str,
    content: Any,
    tool_calls: Any = None,
    tool_call_id: str | None = None,
    user_id: str | None = None,
) -> MessageModel:
    uid = user_id if user_id not in ("anonymous", "legacy", None) else None
    async with async_session_maker() as session:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        s = (await session.execute(stmt)).scalar_one_or_none()
        if not s:
            title = "New Chat"
            if role == "user":
                if isinstance(content, str):
                    title = content[:50]
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            title = part.get("text", "New Chat")[:50]
                            break
            s = SessionModel(id=session_id, title=title, user_id=uid)
            session.add(s)
        else:
            if uid and s.user_id and s.user_id != uid:
                raise PermissionError("Session belongs to another user")
            if uid and not s.user_id:
                s.user_id = uid
            if s.title == "New Chat" and role == "user":
                if isinstance(content, str):
                    s.title = content[:50]
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            s.title = part.get("text", "New Chat")[:50]
                            break
            s.updated_at = datetime.utcnow()

        msg = MessageModel(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg


async def async_get_session_messages_dicts(
    session_id: str,
    user_id: str | None = None,
) -> list[dict]:
    """Return messages for a session formatted for the LLM / UI."""
    if user_id and user_id not in ("anonymous", "legacy"):
        ok = await async_assert_session_access(session_id, user_id)
        if not ok:
            return []

    async with async_session_maker() as session:
        stmt = (
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(MessageModel.created_at.asc())
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()

        formatted = []
        for msg in messages:
            item = {"role": msg.role}
            if msg.content is not None:
                item["content"] = msg.content
            if msg.tool_calls is not None:
                item["tool_calls"] = msg.tool_calls
            if msg.tool_call_id is not None:
                item["tool_call_id"] = msg.tool_call_id
            formatted.append(item)
        return formatted
