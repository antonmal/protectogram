"""Integration tests for inbox deduplication and outbox idempotency."""

import json
import os
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, text

CANNED_UPDATES_DIR = Path(__file__).parent.parent / "contract" / "canned_updates"


def load_canned_update(filename: str) -> dict:
    with open(CANNED_UPDATES_DIR / filename) as f:
        return json.load(f)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_inbox_outbox_idempotency(async_client, respx_mock):
    """Test that duplicate updates are handled correctly with database persistence."""
    # Env for Telegram
    os.environ["TELEGRAM_BOT_TOKEN"] = "123:ABC"
    os.environ["TELEGRAM_WEBHOOK_SECRET"] = "secret123"
    os.environ["TELEGRAM_API_BASE"] = "https://api.telegram.org"
    os.environ["TELEGRAM_ALLOWLIST_CHAT_IDS"] = "1111"

    update = load_canned_update("message_start.json")

    # Mock Telegram API responses
    send_message = respx_mock.post("https://api.telegram.org/bot123:ABC/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "result": {"message_id": 12345}})
    )

    # Send webhook twice with same update
    r1 = await async_client.post(
        "/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
        json=update,
    )
    r2 = await async_client.post(
        "/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret123"},
        json=update,
    )
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Verify interception happened (idempotency => exactly 1 sendMessage)
    assert send_message.called, "respx did not intercept sendMessage"
    assert send_message.call_count == 1

    # DB assertions
    engine = create_engine(os.getenv("APP_DATABASE_URL_SYNC"))
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM inbox_events WHERE provider='telegram'")
        ).scalar_one()
        assert count == 1
        count = conn.execute(
            text("SELECT COUNT(*) FROM outbox_messages WHERE channel='telegram'")
        ).scalar_one()
        assert count == 1
        message_id = conn.execute(
            text("SELECT provider_message_id FROM outbox_messages WHERE channel='telegram'")
        ).scalar()
        assert message_id is not None
    engine.dispose()

    # Cleanup
    for k in [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_WEBHOOK_SECRET",
        "TELEGRAM_API_BASE",
        "TELEGRAM_ALLOWLIST_CHAT_IDS",
    ]:
        os.environ.pop(k, None)
