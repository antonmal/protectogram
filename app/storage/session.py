"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.settings import get_settings


def create_async_engine_from_env() -> AsyncEngine:
    """Create async database engine from environment."""
    settings = get_settings()
    if not settings.app_database_url:
        raise RuntimeError("APP_DATABASE_URL not set")
    return create_async_engine(settings.app_database_url, future=True, pool_pre_ping=True)


def create_sync_engine_from_env():
    """Create sync database engine from environment."""
    settings = get_settings()
    if not settings.app_database_url_sync:
        raise RuntimeError("APP_DATABASE_URL_SYNC not set")
    return create_engine(settings.app_database_url_sync, future=True)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker."""
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    engine = create_async_engine_from_env()
    async_session_maker = get_sessionmaker(engine)

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    await engine.dispose()


def get_sync_session():
    """Get sync database session."""
    engine = create_sync_engine_from_env()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
