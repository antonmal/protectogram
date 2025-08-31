"""Unit tests for metrics."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_metrics_endpoint(app):
    """Test metrics endpoint returns Prometheus format."""
    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

    content = response.text
    # Check for expected metrics
    assert "inbound_events_total" in content
    assert "outbox_sent_total" in content
    assert "outbox_errors_total" in content
