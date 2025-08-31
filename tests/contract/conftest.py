"""Contract test configuration."""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from tests.conftest import reset_settings_cache


@pytest.fixture
def telegram_env():
    """Set up Telegram environment variables."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "123:ABC"
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "secret123"
    os.environ["TELEGRAM_API_BASE"] = "https://api.telegram.org"
    os.environ["TELEGRAM_ALLOWLIST_CHAT_IDS"] = "1111"
    yield
    # Cleanup
    for key in [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_WEBHOOK_SECRET", 
        "TELEGRAM_API_BASE", "TELEGRAM_ALLOWLIST_CHAT_IDS"
    ]:
        os.environ.pop(key, None)


@pytest_asyncio.fixture
async def app_without_db(telegram_env):
    """Create app without database for contract tests."""
    reset_settings_cache()
    from app.main import create_app
    from app.storage.session import get_session
    
    app = create_app()
    
    # Create a mock session that simulates database behavior
    async def mock_get_session():
        session = AsyncMock()
        
        # Track added objects for idempotency simulation
        added_objects = []
        
        # Mock the add method to track added objects (not async)
        def mock_add(obj):
            added_objects.append(obj)
        
        # Mock commit to simulate successful commit (async)
        async def mock_commit():
            pass
        
        # Mock rollback (async)
        async def mock_rollback():
            pass
        
        # Mock execute for queries - simulate idempotency checks (async)
        async def mock_execute(stmt):
            # Create a mock result that can be used for scalar_one()
            result_mock = AsyncMock()
            
            # If this is a query for existing outbox message, return None (not found)
            if "OutboxMessage" in str(stmt) and "idempotency_key" in str(stmt):
                result_mock.scalar_one.return_value = None
            
            return result_mock
        
        session.add = mock_add
        session.commit = mock_commit
        session.rollback = mock_rollback
        session.execute = mock_execute
        
        return session
    
    # Override the get_session dependency
    app.dependency_overrides[get_session] = mock_get_session
    
    return app


@pytest_asyncio.fixture
async def async_client_without_db(app_without_db):
    """Async client without database."""
    from httpx import AsyncClient
    from httpx import ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=app_without_db), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def respx_mock():
    """Function-scoped respx mock for external HTTP calls."""
    import respx
    
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as respx_mock:
        yield respx_mock


# Optional: Import integration fixtures if contract test needs DB
try:
    from tests.integration.conftest import pg_container, db_clean, app, async_client
except ImportError:
    pass
