"""
Memory store for AgenThink.
Uses the async/sync SQLAlchemy database layer (backend.database).
Scoped by request-context user_id when available.
"""

import re

from backend.core.request_context import get_context
from backend.database.repository import (
    async_add_fact as db_async_add_fact,
    async_list_facts as db_async_list_facts,
    async_clear_facts as db_async_clear_facts,
    add_fact_sync,
    list_facts_sync,
    clear_facts_sync,
)


def _uid() -> str | None:
    ctx = get_context()
    uid = ctx.user_id
    if uid in ("anonymous", "legacy", None):
        return None
    return uid


def add_fact(fact: str) -> None:
    add_fact_sync(fact, user_id=_uid())


def list_facts() -> list[str]:
    return list_facts_sync(user_id=_uid())


def clear_facts() -> None:
    clear_facts_sync(user_id=_uid())


async def async_add_fact(fact: str, user_id: str | None = None) -> None:
    await db_async_add_fact(fact, user_id=user_id if user_id is not None else _uid())


async def async_list_facts(user_id: str | None = None) -> list[str]:
    return await db_async_list_facts(user_id=user_id if user_id is not None else _uid())


async def async_clear_facts(user_id: str | None = None) -> None:
    await db_async_clear_facts(user_id=user_id if user_id is not None else _uid())


def format_memory(facts: list[str] | None = None) -> str:
    facts = list_facts() if facts is None else facts
    if not facts:
        return ""
    lines = "\n".join(f"- {fact}" for fact in facts)
    return f"Long-term memory about the user:\n{lines}"


_EXPLICIT_RE = re.compile(
    r"^(?:Nhớ rằng|Remember that)\s+(.+)$",
    flags=re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"^(?:Tên tôi là|My name is)\s+(.+)$",
    flags=re.IGNORECASE,
)
_LIKE_RE = re.compile(
    r"^(?:Tôi thích|I like)\s+(.+)$",
    flags=re.IGNORECASE,
)
_LIVE_RE = re.compile(
    r"^(?:Tôi ở|I live in)\s+(.+)$",
    flags=re.IGNORECASE,
)


def extract_and_store(message: str) -> str | None:
    """Detect memorable facts, store them, and optionally return a confirmation."""
    text = message.strip()

    match = _EXPLICIT_RE.match(text)
    if match:
        fact = match.group(1).strip(" .")
        add_fact(fact)
        return f"Đã nhớ: {fact}"

    match = _NAME_RE.match(text)
    if match:
        name = match.group(1).strip(" .")
        add_fact(f"Tên người dùng là {name}")
        return None

    match = _LIKE_RE.match(text)
    if match:
        liked = match.group(1).strip(" .")
        add_fact(f"Người dùng thích {liked}")
        return None

    match = _LIVE_RE.match(text)
    if match:
        place = match.group(1).strip(" .")
        add_fact(f"Người dùng ở {place}")
        return None

    return None
