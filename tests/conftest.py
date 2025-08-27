"""Test configuration and fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.storage.models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def disable_scheduler_in_tests():
    """Disable scheduler in all tests by default (charter requirement)."""
    # Store original value
    original_value = settings.SCHEDULER_ENABLED

    # Disable scheduler for tests
    settings.SCHEDULER_ENABLED = False

    yield

    # Restore original value
    settings.SCHEDULER_ENABLED = original_value


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Session-scoped Postgres container."""
    with PostgresContainer("postgres:15") as container:
        yield container


@pytest_asyncio.fixture
async def test_engine(postgres_container: PostgresContainer):
    """Create test database engine with Testcontainers."""
    # Get the raw URL from the container
    raw_url = postgres_container.get_connection_url()
    print(f"Raw Testcontainers URL: {raw_url}")

    # Convert to proper formats
    # For sync operations (psycopg2): postgresql://user:pass@host:port/db
    # For async operations (asyncpg): postgresql+asyncpg://user:pass@host:port/db
    if "postgresql+psycopg2://" in raw_url:
        sync_url = raw_url.replace("postgresql+psycopg2://", "postgresql://")
        async_url = raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    else:
        sync_url = raw_url
        async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://")

    print(f"Sync URL: {sync_url}")
    print(f"Async URL: {async_url}")

    # Create tables first using sync engine
    from sqlalchemy import create_engine

    print("Creating tables...")
    sync_engine = create_engine(sync_url)
    try:
        Base.metadata.create_all(sync_engine)
        print("Tables created successfully")

        # Verify tables were created
        with sync_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result]
            print(f"Created tables: {tables}")

    except Exception as e:
        print(f"Table creation failed: {e}")
        raise
    finally:
        sync_engine.dispose()

    # Create async engine for tests with NullPool (no pooled leftovers)
    engine = create_async_engine(
        async_url,
        echo=False,
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    yield engine

    # Clean up
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Tier 1: Function-scoped AsyncSession with SAVEPOINT isolation."""
    # Create one connection per test (not per session)
    connection = await test_engine.connect()

    # Start outer transaction
    outer_trans = await connection.begin()

    # Start nested transaction (SAVEPOINT)
    nested_trans = await connection.begin_nested()

    # Create sessionmaker bound to this specific connection
    sessionmaker = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )

    # Create session from the connection-bound sessionmaker
    session = sessionmaker()

    # Set up event listener to re-open SAVEPOINT after commits
    def re_open_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.is_active:
            # Re-open nested transaction after commit
            connection.begin_nested()

    # Listen for transaction end events
    from sqlalchemy import event

    event.listen(session.sync_session, "after_transaction_end", re_open_savepoint)

    try:
        yield session
    finally:
        # Clean up: rollback nested, rollback outer, close connection
        await session.close()
        if nested_trans.is_active:
            await nested_trans.rollback()
        await outer_trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def async_client(
    test_session: AsyncSession,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create httpx.AsyncClient with ASGI lifespan."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    # Use ASGI transport for httpx.AsyncClient
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "telegram_id": "123456789",
        "phone_e164": "+1234567890",
        "display_name": "Test User",
    }


@pytest.fixture
def sample_member_link_data():
    """Sample member link data for tests."""
    return {
        "watcher_user_id": 1,
        "traveler_user_id": 2,
        "status": "active",
        "call_priority": 1,
        "ring_timeout_sec": 25,
        "max_retries": 2,
        "retry_backoff_sec": 60,
        "telegram_enabled": True,
        "calls_enabled": True,
    }


@pytest.fixture
def sample_incident_data():
    """Sample incident data for tests."""
    return {
        "traveler_user_id": 1,
        "status": "active",
    }


# Tier 2: Concurrent test fixtures (dedicated database, no SAVEPOINT)
@pytest_asyncio.fixture
async def isolated_db(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[tuple[str, AsyncEngine], None]:
    """Tier 2: Create isolated database for concurrent tests (no SAVEPOINT conflicts).

    Uses programmatic migration approach:
    - Creates unique test database
    - Sets ALEMBIC_DATABASE_URL environment variable
    - Runs migrations against test database
    - No dependency on local .env file
    """
    import uuid

    # Create unique database name
    db_name = f"test_{uuid.uuid4().hex[:8]}"

    # Get base URL from container
    base_url = postgres_container.get_connection_url()

    # Create new database
    from sqlalchemy import create_engine, text

    sync_engine = create_engine(base_url)

    try:
        # Create the test database (must use autocommit for CREATE DATABASE)
        with sync_engine.connect() as conn:
            conn.execute(text("COMMIT"))  # End any existing transaction
            conn.execute(text(f"CREATE DATABASE {db_name}"))
            # CREATE DATABASE is auto-committed

        # Build URL for the new database
        if "postgresql+psycopg2://" in base_url:
            test_url = (
                base_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
                + f"/{db_name}"
            )
        else:
            test_url = (
                base_url.replace("postgresql://", "postgresql+asyncpg://")
                + f"/{db_name}"
            )

        # Create async engine for the test database
        test_engine = create_async_engine(
            test_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=False,
        )

        # Run Alembic migrations on the test database using environment variable
        from alembic import command
        from alembic.config import Config

        # Set environment variable for Alembic to use the test database
        sync_test_url = (
            base_url.replace("postgresql+psycopg2://", "postgresql://") + f"/{db_name}"
        )
        os.environ["ALEMBIC_DATABASE_URL"] = sync_test_url

        try:
            # Create Alembic config and run migrations
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
        finally:
            # Clean up environment variable
            os.environ.pop("ALEMBIC_DATABASE_URL", None)

        yield test_url, test_engine

        # Clean up: drop the test database
        await test_engine.dispose()
        with sync_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE {db_name}"))
            conn.commit()

    finally:
        sync_engine.dispose()


@pytest_asyncio.fixture
async def concurrent_session(
    isolated_db: tuple[str, AsyncEngine],
) -> AsyncGenerator[AsyncSession, None]:
    """Tier 2: Session for concurrent tests (no SAVEPOINT, dedicated database)."""
    test_url, test_engine = isolated_db

    # Create normal session (no nested transactions)
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# External API mocking fixtures (charter requirement: "Do not hit external networks in tests")
@pytest.fixture(autouse=True)
def mock_telegram_api():
    """Mock Telegram API calls to prevent external network requests."""
    with patch("app.integrations.telegram.outbox.send_telegram_message") as mock_send:
        mock_send.return_value = True  # Function returns bool
        yield mock_send


@pytest.fixture(autouse=True)
def mock_telnyx_api():
    """Mock Telnyx API calls to prevent external network requests."""
    with patch(
        "app.integrations.telnyx.call_control.create_telnyx_call"
    ) as mock_create_call:
        mock_create_call.return_value = (
            "test_call_id"  # Function returns telnyx_call_id string
        )
        yield mock_create_call


@pytest.fixture(autouse=True)
def mock_telegram_bot():
    """Mock Telegram Bot API calls."""
    with patch("aiogram.Bot.send_message") as mock_send_message:
        mock_send_message.return_value = MagicMock(message_id=12345)
        yield mock_send_message


@pytest.fixture(autouse=True)
def mock_telnyx_client():
    """Mock Telnyx client calls."""
    with patch("telnyx.Call.create") as mock_call_create:
        mock_call_create.return_value = MagicMock(id="test_call_id")
        yield mock_call_create
