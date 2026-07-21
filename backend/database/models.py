"""
SQLAlchemy ORM models for AgenThink database layer.
Supports both PostgreSQL and SQLite.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    rag_project_id = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("UserModel", back_populates="sessions")
    messages = relationship(
        "MessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # 'user', 'assistant', 'tool', 'system'
    content = Column(JSON, nullable=True)  # Can be string or JSON (for multimodal list of dicts)
    tool_calls = Column(JSON, nullable=True)  # List of tool calls if role is 'assistant'
    tool_call_id = Column(String(128), nullable=True)  # Call ID if role is 'tool'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("SessionModel", back_populates="messages")


class MemoryFactModel(Base):
    __tablename__ = "memories"  # Keeps same table name as legacy store
    __table_args__ = (
        UniqueConstraint("user_id", "fact", name="uq_memories_user_fact"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    fact = Column(String(512), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
