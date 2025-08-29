"""Unit tests for health endpoints."""

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient) -> None:
    """Test health live endpoint."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready(async_client: AsyncClient) -> None:
    """Test health ready endpoint."""
    response = await async_client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "starting"}}


def test_health_live_sync(client: Any) -> None:
    """Test health live endpoint with sync client."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_sync(client: Any) -> None:
    """Test health ready endpoint with sync client."""
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "starting"}}
