"""Contract tests for Telegram webhook."""

import os
from pathlib import Path
import json
import httpx
import pytest
import respx
from httpx import AsyncClient

# Load canned updates
CANNED_UPDATES_DIR = Path(__file__).parent / "canned_updates"

def load_canned_update(filename: str) -> dict:
    """Load a canned update from JSON file."""
    with open(CANNED_UPDATES_DIR / filename) as f:
        return json.load(f)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_start_command(async_client_without_db: AsyncClient):
    """Test webhook with /start command."""
    # Load canned update
    update = load_canned_update("message_start.json")
    
    # Mock Telegram API responses with context manager
    async with respx.mock(assert_all_mocked=True) as respx_mock:
        send_message = respx_mock.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 123}})
        )
        
        # Send webhook
        response = await async_client_without_db.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json=update,
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        
        # Verify Telegram API was called
        assert send_message.called
        assert send_message.call_count == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_ping_command(async_client_without_db: AsyncClient):
    """Test webhook with /ping command."""
    # Load canned update
    update = load_canned_update("message_ping.json")
    
    # Mock Telegram API responses with context manager
    async with respx.mock(assert_all_mocked=True) as respx_mock:
        send_message = respx_mock.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 124}})
        )
        
        # Send webhook
        response = await async_client_without_db.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json=update,
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        
        # Verify Telegram API was called
        assert send_message.called
        assert send_message.call_count == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_callback_query(async_client_without_db: AsyncClient):
    """Test webhook with callback query."""
    # Load canned update
    update = load_canned_update("callback_basic.json")
    
    # Mock Telegram API responses with context manager
    async with respx.mock(assert_all_mocked=True) as respx_mock:
        answer_cb = respx_mock.post("https://api.telegram.org/bot123:ABC/answerCallbackQuery").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        send_message = respx_mock.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 125}})
        )
        
        # Send webhook
        response = await async_client_without_db.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json=update,
        )
        
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        
        # Verify Telegram API was called twice (answerCallbackQuery + sendMessage)
        assert answer_cb.called
        assert send_message.called
        assert answer_cb.call_count == 1
        assert send_message.call_count == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_duplicate_replay(async_client_without_db: AsyncClient):
    """Test that duplicate updates are handled correctly."""
    # Load canned update
    update = load_canned_update("message_start.json")
    
    # Mock Telegram API responses with context manager
    async with respx.mock(assert_all_mocked=True) as respx_mock:
        send_message = respx_mock.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 126}})
        )
        
        # Send webhook twice with same update
        response1 = await async_client_without_db.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json=update,
        )
        
        response2 = await async_client_without_db.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
            json=update,
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify Telegram API was called only once (duplicate was dropped)
        assert send_message.called
        assert send_message.call_count == 1


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_missing_header(async_client_without_db: AsyncClient):
    """Test webhook without secret header."""
    update = load_canned_update("message_start.json")
    
    response = await async_client_without_db.post(
        "/telegram/webhook",
        json=update,
    )
    
    assert response.status_code == 401


@pytest.mark.contract
@pytest.mark.asyncio
async def test_webhook_wrong_secret(async_client_without_db: AsyncClient):
    """Test webhook with wrong secret."""
    update = load_canned_update("message_start.json")
    
    response = await async_client_without_db.post(
        "/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
        json=update,
    )
    
    assert response.status_code == 401
