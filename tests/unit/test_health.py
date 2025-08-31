"""Unit tests for health endpoints."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_live(app):
    """Test health live endpoint."""
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.unit
def test_health_ready_no_db(app):
    """Test health ready endpoint without database."""
    # Ensure no database URLs are set
    os.environ.pop("APP_DATABASE_URL", None)
    os.environ.pop("APP_DATABASE_URL_SYNC", None)

    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert "detail" in data
    assert data["detail"]["status"] == "unready"


@pytest.mark.unit
def test_metrics_endpoint(app):
    """Test metrics endpoint."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

    content = response.text
    assert "inbound_events_total" in content
    assert "outbox_sent_total" in content
    assert "outbox_errors_total" in content
