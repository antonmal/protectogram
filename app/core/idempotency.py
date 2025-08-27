"""Idempotency utilities for Inbox/Outbox pattern."""

import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import InboxEvent, OutboxMessage


def generate_idempotency_key(data: dict[str, Any]) -> str:
    """Generate idempotency key from data."""
    # Sort keys to ensure consistent hashing
    sorted_data = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(sorted_data.encode()).hexdigest()


def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return str(uuid4())


async def is_duplicate_inbox_event(
    session: AsyncSession,
    provider: str,
    provider_event_id: str,
) -> bool:
    """Check if inbox event is duplicate."""
    result = await session.execute(
        text(
            "SELECT 1 FROM inbox_events WHERE provider = :provider AND provider_event_id = :event_id"
        ),
        {"provider": provider, "event_id": provider_event_id},
    )
    return result.scalar() is not None


async def store_inbox_event(
    session: AsyncSession,
    provider: str,
    provider_event_id: str,
    payload: dict[str, Any],
) -> InboxEvent:
    """Store inbox event for idempotency."""
    event = InboxEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        payload_json=json.dumps(payload),
    )
    session.add(event)
    await session.commit()
    return event


async def is_duplicate_outbox_message(
    session: AsyncSession,
    idempotency_key: str,
) -> bool:
    """Check if outbox message is duplicate."""
    result = await session.execute(
        text("SELECT 1 FROM outbox_messages WHERE idempotency_key = :key"),
        {"key": idempotency_key},
    )
    return result.scalar() is not None


async def store_outbox_message(
    session: AsyncSession,
    channel: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> OutboxMessage:
    """Store outbox message for idempotency."""
    message = OutboxMessage(
        channel=channel,
        idempotency_key=idempotency_key,
        payload_json=json.dumps(payload),
        status="pending",
    )
    session.add(message)
    await session.commit()
    return message


async def mark_outbox_sent(
    session: AsyncSession,
    message_id: int,
    provider_message_id: str,
) -> None:
    """Mark outbox message as sent."""
    await session.execute(
        text("""
        UPDATE outbox_messages
        SET status = 'sent', provider_message_id = :provider_id, updated_at = NOW()
        WHERE id = :message_id
        """),
        {"provider_id": provider_message_id, "message_id": message_id},
    )
    await session.commit()


async def mark_outbox_failed(
    session: AsyncSession,
    message_id: int,
    error: str,
) -> None:
    """Mark outbox message as failed."""
    await session.execute(
        text("""
        UPDATE outbox_messages
        SET status = 'failed', updated_at = NOW()
        WHERE id = :message_id
        """),
        {"message_id": message_id},
    )
    await session.commit()
