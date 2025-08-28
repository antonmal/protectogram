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


def _normalize_asyncpg_url(raw: str) -> tuple[str, dict]:
    """
    Normalize any Postgres URL for SQLAlchemy+asyncpg and remove sslmode:
    - postgres:// → postgresql+asyncpg://
    - postgresql:// → postgresql+asyncpg://
    - If host is private (*.internal or fdaa:), enforce ssl=disable and empty connect_args
    - Else enforce ssl=require (URL param) and connect_args={"ssl": "require"}
    - Remove any 'sslmode' from query entirely (asyncpg doesn't accept it)
    """
    if not raw:
        raise RuntimeError("Database URL is empty")

    # driver normalization
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    parts = urlsplit(raw)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))

    # remove sslmode completely
    if "sslmode" in q:
        q.pop("sslmode", None)

    host = (parts.hostname or "").lower()
    is_internal = host.endswith(".internal") or host.startswith("fdaa:")

    if is_internal:
        q["ssl"] = "disable"
        connect_args = {}
    else:
        q["ssl"] = "require"
        connect_args = {"ssl": "require"}

    # rebuild query
    raw = urlunsplit(parts._replace(query=urlencode(q)))

    return raw, connect_args


# Lazy engine creation
_engine: AsyncEngine | None = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        db_url, connect_args = _normalize_asyncpg_url(settings.POSTGRES_URL)
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
