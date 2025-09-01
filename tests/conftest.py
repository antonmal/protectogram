"""Test configuration and fixtures for Protectogram tests."""

import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop

    # Clean up
    try:
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_settings():
    """Get test-specific settings."""
    return get_settings()


@pytest.fixture
def sync_client():
    """Create a synchronous test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client with proper cleanup."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def test_db_session(test_settings):
    """Create a test database session with proper cleanup."""
    # For now, use the existing database setup
    # In a full test suite, you'd want to use a separate test database
    engine = create_async_engine(
        test_settings.async_database_url,
        echo=test_settings.log_sql,
        future=True,
    )

    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return session_maker


class TestUser:
    """Test user data helper."""

    @staticmethod
    def create_test_user_data(telegram_id: int = None):
        """Create test user data with unique IDs."""
        if telegram_id is None:
            telegram_id = 100000000 + hash(str(id(object()))) % 900000000

        return {
            "telegram_user_id": telegram_id,
            "first_name": "Test",
            "last_name": "User",
            "phone_number": f"+34{telegram_id % 1000000000}",
            "preferred_language": "en",
            "gender": "male",
        }

    @staticmethod
    def create_test_guardian_data(telegram_id: int = None):
        """Create test guardian data with unique IDs."""
        if telegram_id is None:
            telegram_id = 200000000 + hash(str(id(object()))) % 800000000

        return {
            "telegram_user_id": telegram_id,
            "phone_number": f"+34{telegram_id % 1000000000}",
            "name": "Test Guardian",
            "gender": "female",
        }


@pytest.fixture
def test_user_data():
    """Generate unique test user data."""
    return TestUser.create_test_user_data()


@pytest.fixture
def test_guardian_data():
    """Generate unique test guardian data."""
    return TestUser.create_test_guardian_data()


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set asyncio mode to auto
    config.option.asyncio_mode = "auto"

    # Configure logging
    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
