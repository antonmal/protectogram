"""Telegram outbox for sending messages - Prompt 4 implementation."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.idempotency import (
    generate_idempotency_key,
    is_duplicate_outbox_message,
    mark_outbox_failed,
    mark_outbox_sent,
    store_outbox_message,
)
from app.core.logging import get_logger
from app.core.metrics import telegram_messages_sent

logger = get_logger(__name__)


async def send_confirmation_message(
    session: AsyncSession,
    chat_id: int,
    message: str,
    correlation_id: str | None = None,
) -> None:
    """Send confirmation message via Telegram (Prompt 4 implementation)."""
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(payload)

    # Check for duplicate
    if await is_duplicate_outbox_message(session, idempotency_key):
        logger.info(
            "Duplicate Telegram message ignored", idempotency_key=idempotency_key[:8]
        )
        return

    try:
        # Store outbox message
        outbox_message = await store_outbox_message(
            session,
            "telegram",
            idempotency_key,
            payload,
        )

        # Send message via Telegram API
        success = await send_telegram_message(payload)

        if success:
            await mark_outbox_sent(session, outbox_message.id, "telegram_msg_id")
            telegram_messages_sent.labels(message_type="confirmation").inc()

            logger.info(
                "Telegram confirmation sent",
                chat_id=chat_id,
                correlation_id=correlation_id,
            )
        else:
            await mark_outbox_failed(session, outbox_message.id, "Failed to send")

    except Exception as e:
        logger.error(
            "Failed to send Telegram confirmation",
            chat_id=chat_id,
            error=str(e),
        )


async def send_telegram_message(payload: dict[str, Any]) -> bool:
    """Send message via Telegram Bot API."""
    try:
        import httpx

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)

            if response.status_code == 200:
                return True
            else:
                logger.error(
                    "Telegram API error",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

    except Exception as e:
        logger.error("Failed to send Telegram message", error=str(e))
        return False


# Domain-specific functions will be implemented in Prompt 6
# For now, we only have the core message sending infrastructure
