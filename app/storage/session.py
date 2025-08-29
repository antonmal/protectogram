"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_async_engine(url: str) -> AsyncEngine:
    """Create async database engine."""
    return create_async_engine(url, future=True, pool_pre_ping=True)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker."""
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    from app.core.settings import settings

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL not set")

    engine = get_async_engine(settings.database_url)
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
