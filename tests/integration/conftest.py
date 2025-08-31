"""Integration test configuration with Testcontainers."""

import os
import pytest
import pytest_asyncio
import time
from typing import Generator

try:
    from testcontainers.postgres import PostgresContainer
    from docker.errors import DockerException, ImageNotFound
    _HAS_TESTCONTAINERS = True
except Exception:
    _HAS_TESTCONTAINERS = False


@pytest.fixture(scope="session", autouse=True)
def _ensure_testcontainers_available():
    """Ensure Testcontainers is available for integration tests."""
    if not _HAS_TESTCONTAINERS:
        pytest.skip("Docker/Testcontainers not available", allow_module_level=True)


@pytest.fixture(scope="session", autouse=True)
def pg_container() -> Generator[dict, None, None]:
    """Start a Postgres container for integration tests."""
    pg = PostgresContainer("postgres:16")
    pg.with_env("POSTGRES_DB", "protectogram_test")
    pg.with_env("POSTGRES_USER", "protectogram_test")
    pg.with_env("POSTGRES_PASSWORD", "protectogram_test")
    
    try:
        print("Starting Postgres container...")
        pg.start()
        print(f"Postgres container started on port {pg.get_exposed_port(5432)}")
        
        # Wait for container to be ready
        time.sleep(2)
        
    except (DockerException, ImageNotFound) as e:
        pytest.skip(f"Docker/Testcontainers unavailable: {e}", allow_module_level=True)
    except Exception as e:
        pytest.skip(f"Postgres container startup failed: {e}", allow_module_level=True)
    
    try:
        # Build database URLs
        base_sync_url = pg.get_connection_url()
        url_sync = base_sync_url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        url_async = base_sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        
        print(f"Sync URL: {url_sync}")
        print(f"Async URL: {url_async}")

        # Set environment variables
        os.environ["APP_DATABASE_URL_SYNC"] = url_sync
        os.environ["APP_DATABASE_URL"] = url_async
        os.environ["ALEMBIC_DATABASE_URL"] = url_sync

        # Apply migrations
        print("Applying Alembic migrations...")
        from alembic.config import Config
        from alembic import command
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
        print("Migrations applied successfully")

        yield {"url_sync": url_sync, "url_async": url_async}
    finally:
        print("Stopping Postgres container...")
        pg.stop()
        print("Postgres container stopped")


@pytest.fixture
def db_clean(pg_container):
    """Clean database before each test."""
    from tests.conftest import reset_settings_cache
    from app.storage.session import create_sync_engine_from_env
    from sqlalchemy import text
    
    # Clear settings cache to pick up the container URLs
    reset_settings_cache()
    
    engine = create_sync_engine_from_env()
    
    # Truncate all tables
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE inbox_events, outbox_messages RESTART IDENTITY CASCADE"))
        conn.commit()
    
    engine.dispose()


@pytest_asyncio.fixture
async def app(db_clean):
    """Create a fresh FastAPI app for each test."""
    from tests.conftest import reset_settings_cache
    from app.main import create_app
    
    reset_settings_cache()
    return create_app()


@pytest_asyncio.fixture
async def async_client(app):
    """Async client fixture for integration tests."""
    from httpx import AsyncClient
    from httpx import ASGITransport
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def respx_mock():
    """Function-scoped respx mock for external HTTP calls."""
    import respx
    
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as respx_mock:
        yield respx_mock
