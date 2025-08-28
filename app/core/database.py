"""Database connection and session management."""

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def normalize_asyncpg_url(raw: str) -> tuple[str, dict]:
    """
    Returns (url, connect_args) suitable for asyncpg.
    - Converts postgres:// → postgresql+asyncpg://
    - Sets ssl=disable for Fly internal hosts (*.internal or fdaa:)
    - Sets ssl=require otherwise
    """
    # driver
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    parts = urlsplit(raw)
    host = parts.hostname or ""
    q = dict(parse_qsl(parts.query, keep_blank_values=True))

    is_internal = host.endswith(".internal") or host.startswith("fdaa:")
    if is_internal:
        q["ssl"] = "disable"
        connect_args = {}  # no SSL for internal
    else:
        q["ssl"] = "require"
        connect_args = {"ssl": "require"}  # asyncpg accepts this

    raw = urlunsplit(parts._replace(query=urlencode(q)))
    return raw, connect_args


# Lazy engine creation
_engine: AsyncEngine | None = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        db_url, connect_args = normalize_asyncpg_url(settings.POSTGRES_URL)
        _engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            poolclass=NullPool,  # Use NullPool for serverless environments
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with get_session_factory()() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection."""
    async with get_engine().begin() as conn:
        # Test connection
        await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database connections."""
    await get_engine().dispose()
