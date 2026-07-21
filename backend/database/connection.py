"""
Database connection and session factory for AgenThink.
Automatically normalizes connection strings for asyncpg (PostgreSQL) and aiosqlite (SQLite).
"""

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.core.config import settings
from backend.database.models import Base

logger = logging.getLogger(__name__)


def get_normalized_db_url(url: str) -> str:
    """Ensure database URL uses async driver (aiosqlite or asyncpg)."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


DATABASE_URL = get_normalized_db_url(settings.DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True if "postgresql" in DATABASE_URL else False,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _soft_migrate(conn) -> None:
    """Add multi-user columns to existing DBs without wiping data."""
    is_sqlite = "sqlite" in DATABASE_URL

    async def _has_column(table: str, column: str) -> bool:
        if is_sqlite:
            rows = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
            return any(r[1] == column for r in rows)
        rows = (
            await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": column},
            )
        ).fetchall()
        return bool(rows)

    async def _table_exists(table: str) -> bool:
        if is_sqlite:
            rows = (
                await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                    {"t": table},
                )
            ).fetchall()
            return bool(rows)
        rows = (
            await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
                ),
                {"t": table},
            )
        ).fetchall()
        return bool(rows)

    try:
        if await _table_exists("sessions") and not await _has_column("sessions", "user_id"):
            await conn.execute(text("ALTER TABLE sessions ADD COLUMN user_id VARCHAR(36)"))
            logger.info("Migrated sessions.user_id")
        if await _table_exists("memories") and not await _has_column("memories", "user_id"):
            await conn.execute(text("ALTER TABLE memories ADD COLUMN user_id VARCHAR(36)"))
            logger.info("Migrated memories.user_id")
    except Exception as exc:
        logger.warning("Soft migrate skipped/partial: %s", exc)


async def init_db() -> None:
    """Initialize database tables and soft-migrate multi-user columns."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _soft_migrate(conn)
        logger.info(
            "Database initialized successfully with URL scheme: %s",
            DATABASE_URL.split("://")[0],
        )
        await _seed_demo_user()
    except Exception as exc:
        logger.error("Failed to initialize database tables: %s", exc)
        raise


async def _seed_demo_user() -> None:
    """Optional demo user for compose (placeholder credentials only)."""
    if not settings.SEED_DEMO_USER:
        return
    from backend.core.security import hash_password
    from backend.database.repository import async_create_user, async_get_user_by_email

    email = (settings.DEMO_USER_EMAIL or "demo@local").strip().lower()
    password = settings.DEMO_USER_PASSWORD or "change-me"
    existing = await async_get_user_by_email(email)
    if existing:
        return
    try:
        await async_create_user(email, hash_password(password))
        logger.info("Seeded demo user %s (change password in production)", email)
    except Exception as exc:
        logger.warning("Demo user seed skipped: %s", exc)


async def get_db_session() -> AsyncSession:
    """Dependency / helper for acquiring database sessions."""
    async with async_session_maker() as session:
        yield session
