"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.config.settings import SettingsFactory
from app.models.base import Base
import os

# Get settings using factory pattern
environment = os.getenv("ENVIRONMENT", "development")
settings = SettingsFactory.create(environment)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_recycle=3600
    if settings.environment == "production"
    else 300,  # 1 hour in prod, 5 min in dev
    pool_size=20
    if settings.environment == "production"
    else 10,  # More connections in prod
    max_overflow=30
    if settings.environment == "production"
    else 10,  # Allow more overflow in prod
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for migrations and utilities
sync_database_url = settings.database_url.replace("+asyncpg", "")


async def get_db() -> AsyncSession:
    """Get database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


sync_engine = create_engine(
    sync_database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_recycle=3600
    if settings.environment == "production"
    else 300,  # 1 hour in prod, 5 min in dev
    pool_size=10
    if settings.environment == "production"
    else 5,  # More connections in prod
    max_overflow=20
    if settings.environment == "production"
    else 5,  # Allow more overflow in prod
)

# Sync session factory
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db():
    """Get sync database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sync_db_session():
    """Get sync database session for use in context managers (Celery tasks)."""
    return SessionLocal()


async def create_tables():
    """Create all tables in the database."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all tables in the database."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
