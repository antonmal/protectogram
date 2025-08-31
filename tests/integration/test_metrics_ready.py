"""Integration tests for metrics and readiness endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ready_with_container(async_client):
    """Test health readiness endpoint with database."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_with_container(async_client):
    """Test metrics endpoint with database."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    
    # Check for expected metrics
    assert "inbound_events_total" in content
    assert "outbox_sent_total" in content
    assert "outbox_errors_total" in content
