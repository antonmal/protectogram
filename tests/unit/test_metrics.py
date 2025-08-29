"""Unit tests for metrics endpoint."""

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_metrics(async_client: Any) -> None:
    """Test metrics endpoint."""
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Check that it contains some basic Prometheus metrics
    content = response.text
    assert "python_info" in content or "process_cpu_seconds" in content


def test_metrics_sync(client: Any) -> None:
    """Test metrics endpoint with sync client."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    # Check that it contains some basic Prometheus metrics
    content = response.text
    assert "python_info" in content or "process_cpu_seconds" in content
