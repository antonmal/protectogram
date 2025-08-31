"""Telegram outbox for idempotent message sending."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.telegram.client import TelegramAPIError, TelegramClient
from app.observability.metrics import outbox_errors_total, outbox_sent_total
from app.storage.models import OutboxMessage

logger = logging.getLogger(__name__)


class SendResult:
    """Result of sending a message."""

    def __init__(
        self,
        success: bool,
        message_id: str | None = None,
        error: str | None = None,
        already_sent: bool = False,
    ) -> None:
        self.success = success
        self.message_id = message_id
        self.error = error
        self.already_sent = already_sent


def build_keyboard(buttons: list[list[tuple[str, str]]]) -> dict[str, Any]:
    """Build a Telegram inline keyboard."""
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": callback_data} for text, callback_data in row]
            for row in buttons
        ]
    }


class TelegramOutbox:
    """Telegram outbox for idempotent message sending."""

    def __init__(self, client: TelegramClient) -> None:
        """Initialize outbox with client."""
        self.client = client

    async def send_text(
        self,
        session: AsyncSession,
        chat_id: int,
        text: str,
        idempotency_key: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> SendResult:
        """Send a text message with idempotency."""
        # Build payload
        payload = {
            "chat_id": chat_id,
            "text": text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        # Try to insert outbox record
        outbox_message = OutboxMessage(
            channel="telegram",
            idempotency_key=idempotency_key,
            payload_json=payload,
            status="pending",
        )

        try:
            session.add(outbox_message)
            await session.commit()
        except IntegrityError:
            # Message already sent, fetch existing record
            await session.rollback()
            stmt = select(OutboxMessage).where(OutboxMessage.idempotency_key == idempotency_key)
            result = await session.execute(stmt)
            existing = result.scalar_one()

            if existing.status == "sent" and existing.provider_message_id:
                return SendResult(
                    success=True,
                    message_id=existing.provider_message_id,
                    already_sent=True,
                )
            else:
                # Message failed before, retry
                pass

        # Send via Telegram API
        try:
            response = await self.client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
            )

            # Update outbox record
            outbox_message.status = "sent"
            outbox_message.provider_message_id = str(response["result"]["message_id"])
            await session.commit()

            # Increment metrics
            outbox_sent_total.labels(channel="telegram").inc()

            return SendResult(
                success=True,
                message_id=str(response["result"]["message_id"]),
            )

        except TelegramAPIError as e:
            # Update outbox record with error
            outbox_message.status = "error"
            await session.commit()

            # Increment metrics
            outbox_errors_total.labels(channel="telegram").inc()

            logger.error(
                "Failed to send Telegram message",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                    "idempotency_key": idempotency_key,
                },
            )

            return SendResult(success=False, error=str(e))
        except Exception as e:
            # Update outbox record with error
            outbox_message.status = "error"
            await session.commit()

            # Increment metrics
            outbox_errors_total.labels(channel="telegram").inc()

            logger.error(
                "Unexpected error sending Telegram message",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                    "idempotency_key": idempotency_key,
                },
            )

            return SendResult(success=False, error=str(e))
