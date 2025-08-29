"""Database configuration and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Database engine (placeholder - will be configured when DATABASE_URL is set)
engine = None
async_session_maker = None


def init_database() -> None:
    """Initialize database connection."""
    global engine, async_session_maker

    if settings.database_url:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.app_env == "local",
            pool_pre_ping=True,
        )
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
