"""
Database module initialization.
"""

from backend.database.connection import engine, init_db, get_db_session
from backend.database.models import Base, SessionModel, MessageModel, MemoryFactModel, UserModel
from backend.database.repository import (
    async_add_fact,
    async_list_facts,
    async_clear_facts,
    add_fact_sync,
    list_facts_sync,
    clear_facts_sync,
    async_list_sessions,
    async_delete_session,
    async_save_message,
    async_get_session_messages_dicts,
    async_get_or_create_session,
    async_create_user,
    async_get_user_by_email,
    async_get_user_by_id,
)

__all__ = [
    "engine",
    "init_db",
    "get_db_session",
    "Base",
    "SessionModel",
    "MessageModel",
    "MemoryFactModel",
    "UserModel",
    "async_add_fact",
    "async_list_facts",
    "async_clear_facts",
    "add_fact_sync",
    "list_facts_sync",
    "clear_facts_sync",
    "async_list_sessions",
    "async_delete_session",
    "async_save_message",
    "async_get_session_messages_dicts",
    "async_get_or_create_session",
    "async_create_user",
    "async_get_user_by_email",
    "async_get_user_by_id",
]
