"""Unit tests for health endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import create_app


def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_health_live(client: TestClient) -> None:
    """Test health live endpoint."""
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["content-type"] == "application/json"


@patch("app.api.health._check_database")
@patch("app.api.health._check_scheduler")
async def test_health_ready_success(
    mock_check_scheduler: AsyncMock,
    mock_check_database: AsyncMock,
    client: TestClient,
) -> None:
    """Test health ready endpoint when all checks pass."""
    mock_check_database.return_value = True
    mock_check_scheduler.return_value = True

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@patch("app.api.health._check_database")
@patch("app.api.health._check_scheduler")
async def test_health_ready_database_failure(
    mock_check_scheduler: AsyncMock,
    mock_check_database: AsyncMock,
    client: TestClient,
) -> None:
    """Test health ready endpoint when database check fails."""
    mock_check_database.return_value = False
    mock_check_scheduler.return_value = True

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"status": "unready", "errors": ["database_connection_failed"]}
    }


@patch("app.api.health._check_database")
@patch("app.api.health._check_scheduler")
async def test_health_ready_scheduler_failure(
    mock_check_scheduler: AsyncMock,
    mock_check_database: AsyncMock,
    client: TestClient,
) -> None:
    """Test health ready endpoint when scheduler check fails."""
    mock_check_database.return_value = True
    mock_check_scheduler.return_value = False

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "unready", "errors": ["scheduler_unhealthy"]}}


def test_metrics_endpoint(client: TestClient) -> None:
    """Test metrics endpoint."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert "scheduler_job_lag_seconds" in response.text
