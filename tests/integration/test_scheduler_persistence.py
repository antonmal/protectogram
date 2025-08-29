"""Integration tests for scheduler persistence."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.scheduler.setup import get_scheduler, shutdown_scheduler, start_scheduler
from tests.integration.conftest import PostgresContainerInfo


@pytest.fixture
def test_app() -> FastAPI:
    """Create test app with scheduler."""
    return create_app()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


@pytest.mark.asyncio
async def test_scheduler_persistence(
    pg_container: PostgresContainerInfo, client: TestClient
) -> None:
    """Test that scheduled jobs persist across scheduler restarts."""
    # Set environment for scheduler
    import os

    os.environ["APP_DATABASE_URL_SYNC"] = pg_container.url_sync
    os.environ["APP_DATABASE_URL"] = pg_container.url_async
    os.environ["SCHEDULER_ENABLED"] = "true"

    # Start scheduler
    await start_scheduler()

    try:
        # Verify scheduler is running
        scheduler = get_scheduler()
        assert scheduler.running, "Scheduler should be running"

        # Verify heartbeat job is registered
        jobs = scheduler.get_jobs()
        heartbeat_jobs = [job for job in jobs if job.id == "heartbeat"]
        assert len(heartbeat_jobs) == 1, "Heartbeat job should be registered"

        # Verify jobstore is accessible
        jobstore = scheduler._jobstores["default"]
        assert jobstore is not None, "Jobstore should be accessible"

    finally:
        await shutdown_scheduler()
