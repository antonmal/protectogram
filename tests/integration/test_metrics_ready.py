"""Integration tests for metrics and readiness endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from tests.integration.conftest import PostgresContainerInfo


@pytest.fixture
def test_app() -> FastAPI:
    """Create test app."""
    return create_app()


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(test_app)


def test_health_ready_with_container(
    pg_container: PostgresContainerInfo, client: TestClient
) -> None:
    """Test health ready endpoint with real database."""
    # Set environment
    import os

    os.environ["APP_DATABASE_URL_SYNC"] = pg_container.url_sync
    os.environ["APP_DATABASE_URL"] = pg_container.url_async
    os.environ["SCHEDULER_ENABLED"] = "true"

    # Start scheduler first
    import asyncio

    from app.scheduler.setup import shutdown_scheduler, start_scheduler

    async def run_test() -> None:
        await start_scheduler()
        try:
            response = client.get("/health/ready")

            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")

            assert response.status_code == 200
            assert response.json() == {"status": "ready"}
        finally:
            await shutdown_scheduler()

    asyncio.run(run_test())


def test_metrics_with_container(pg_container: PostgresContainerInfo, client: TestClient) -> None:
    """Test metrics endpoint with real database."""
    # Set environment
    import os

    os.environ["APP_DATABASE_URL_SYNC"] = pg_container.url_sync
    os.environ["APP_DATABASE_URL"] = pg_container.url_async
    os.environ["SCHEDULER_ENABLED"] = "true"

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert "scheduler_job_lag_seconds" in response.text
    assert "health_ready_checks_total" in response.text
