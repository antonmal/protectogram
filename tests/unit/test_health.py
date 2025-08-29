"""Unit tests for health endpoints."""

import pytest
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
    assert response.json() == {"status": "live"}
    assert response.headers["content-type"] == "application/json"


def test_health_ready(client: TestClient) -> None:
    """Test health ready endpoint."""
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert response.headers["content-type"] == "application/json"
