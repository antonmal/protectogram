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


def _normalize_asyncpg_url(url: str) -> str:
    """Normalize database URL for asyncpg compatibility."""
    # ensure async driver
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    # rewrite sslmode -> ssl
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    if "sslmode" in q:
        # map libpq-style values to asyncpg 'ssl' values
        m = {
            "disable": "disable",
            "prefer": "prefer",
            "allow": "allow",
            "require": "require",
            "verify-ca": "verify-ca",
            "verify-full": "verify-full",
        }
        q["ssl"] = m.get(q["sslmode"], "require")
        del q["sslmode"]
        parts = parts._replace(query=urlencode(q))
        url = urlunsplit(parts)
    return url


# Lazy engine creation
_engine: AsyncEngine | None = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        normalized_url = _normalize_asyncpg_url(settings.POSTGRES_URL)
        _engine = create_async_engine(
            normalized_url,
            echo=settings.DEBUG,
            poolclass=NullPool,  # Use NullPool for serverless environments
            future=True,
            connect_args={"ssl": "require"},  # safe default for Fly Postgres
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
