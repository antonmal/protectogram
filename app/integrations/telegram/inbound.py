"""Telegram inbound message processing."""

import hashlib
import logging
from typing import Any

from aiogram.types import Update

from app.integrations.telegram.outbox import TelegramOutbox
from app.integrations.telegram.parsing import extract_chat_id
from app.observability.metrics import inbound_events_total

logger = logging.getLogger(__name__)


class InboundResult:
    """Result of processing an inbound message."""

    def __init__(
        self,
        processed: bool,
        chat_id: int | None = None,
        message_type: str | None = None,
        error: str | None = None,
    ) -> None:
        self.processed = processed
        self.chat_id = chat_id
        self.message_type = message_type
        self.error = error


def check_allowlist(chat_id: int, allowlist: str | None) -> bool:
    """Check if chat ID is in allowlist."""
    if not allowlist:
        return True

    allowed_ids = [int(x.strip()) for x in allowlist.split(",") if x.strip()]
    return chat_id in allowed_ids


def generate_idempotency_key(chat_id: int, text: str) -> str:
    """Generate idempotency key for outbox."""
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    return f"telegram:{chat_id}:{text_hash}"


async def process_inbound(
    update: Update,
    outbox: TelegramOutbox,
    session: Any,  # AsyncSession
    allowlist: str | None = None,
) -> InboundResult:
    """Process an inbound Telegram update."""
    # Convert Update to dict for parsing
    update_dict = update.model_dump()
    chat_id = extract_chat_id(update_dict)
    message_type = None

    # Check allowlist
    if chat_id and not check_allowlist(chat_id, allowlist):
        logger.info(
            "Ignoring message from non-allowed chat",
            extra={"chat_id": chat_id, "update_id": update.update_id},
        )
        return InboundResult(processed=False, chat_id=chat_id)

    # Handle message
    if update.message:
        message_type = "message"
        inbound_events_total.labels(provider="telegram", type="message").inc()

        if update.message.text:
            text = update.message.text.strip()

            if text == "/ping" and chat_id is not None:
                response_text = "pong"
                idempotency_key = generate_idempotency_key(chat_id, response_text)

                result = await outbox.send_text(
                    session=session,
                    chat_id=chat_id,
                    text=response_text,
                    idempotency_key=idempotency_key,
                )

                if not result.success:
                    logger.error(
                        "Failed to send ping response",
                        extra={"chat_id": chat_id, "error": result.error},
                    )

            elif text == "/start" and chat_id is not None:
                response_text = "👋 Привет! Бот подключен."
                idempotency_key = generate_idempotency_key(chat_id, response_text)

                result = await outbox.send_text(
                    session=session,
                    chat_id=chat_id,
                    text=response_text,
                    idempotency_key=idempotency_key,
                )

                if not result.success:
                    logger.error(
                        "Failed to send start response",
                        extra={"chat_id": chat_id, "error": result.error},
                    )

    # Handle callback query
    elif update.callback_query:
        message_type = "callback_query"
        inbound_events_total.labels(provider="telegram", type="callback_query").inc()

        callback_query = update.callback_query

        # Answer callback query
        try:
            await outbox.client.answer_callback_query(
                callback_query_id=callback_query.id,
                text=None,
                show_alert=False,
            )
        except Exception as e:
            logger.error(
                "Failed to answer callback query",
                extra={"callback_query_id": callback_query.id, "error": str(e)},
            )

        # Send acknowledgment message if we have a chat
        if chat_id is not None:
            response_text = "✅ Клик получен."
            idempotency_key = generate_idempotency_key(chat_id, response_text)

            result = await outbox.send_text(
                session=session,
                chat_id=chat_id,
                text=response_text,
                idempotency_key=idempotency_key,
            )

            if not result.success:
                logger.error(
                    "Failed to send callback acknowledgment",
                    extra={"chat_id": chat_id, "error": result.error},
                )

    return InboundResult(
        processed=True,
        chat_id=chat_id,
        message_type=message_type,
    )
