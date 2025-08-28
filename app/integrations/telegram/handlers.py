"""Telegram message handlers for Prompt 4 - Telegram primitives."""

from typing import Any

from app.core.logging import get_logger
from app.core.services import TelegramService

logger = get_logger(__name__)


async def handle_telegram_update(
    update_data: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> bool:
    """
    Handle incoming Telegram update with deduplication.

    Returns True if update was processed, False if duplicate.
    """
    update_id = update_data.get("update_id")
    if not update_id:
        logger.warning("Update missing update_id", update_data=update_data)
        return False

    # Check for duplicate update_id
    if await telegram_service.is_duplicate_event("telegram", str(update_id)):
        logger.info("Duplicate update_id, skipping", update_id=update_id)
        return False

    # Store in inbox_events for deduplication
    await telegram_service.store_inbox_event("telegram", str(update_id), update_data)

    # Process the update
    await _process_telegram_update(update_data, telegram_service, correlation_id)

    return True


async def _process_telegram_update(
    update_data: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Process Telegram update (internal function)."""
    # Handle different update types
    if "message" in update_data:
        await _handle_message(update_data["message"], telegram_service, correlation_id)
    elif "callback_query" in update_data:
        await _handle_callback_query(
            update_data["callback_query"], telegram_service, correlation_id
        )
    else:
        logger.info("Unhandled update type", update_type=list(update_data.keys()))


async def _handle_message(
    message: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle incoming Telegram message."""
    text = message.get("text", "").strip()
    chat_id = message.get("chat", {}).get("id")
    user_data = message.get("from", {})

    if not chat_id or not user_data:
        logger.warning("Invalid message format", message=message)
        return

    # Get or create user
    user = await telegram_service.get_or_create_user(
        str(user_data.get("id")),
        user_data.get("first_name", "Unknown User"),
    )

    logger.info(
        "Received message",
        chat_id=chat_id,
        user_id=user.id,
        text=text[:50] + "..." if len(text) > 50 else text,
        correlation_id=correlation_id,
    )

    # For Prompt 4: Just send a confirmation message
    # Domain logic will be implemented in Prompt 6
    await telegram_service.send_confirmation_message(chat_id, "Message received")


async def _handle_callback_query(
    callback_query: dict[str, Any],
    telegram_service: TelegramService,
    correlation_id: str | None = None,
) -> None:
    """Handle Telegram callback query (button press)."""
    data = callback_query.get("data", "")
    user_data = callback_query.get("from", {})
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")

    if not data or not user_data:
        logger.warning("Invalid callback query", callback_query=callback_query)
        return

    # Get user
    user = await telegram_service.get_or_create_user(
        str(user_data.get("id")),
        user_data.get("first_name", "Unknown User"),
    )

    logger.info(
        "Received callback query",
        data=data,
        user_id=user.id,
        chat_id=chat_id,
        correlation_id=correlation_id,
    )

    # For Prompt 4: Just send a confirmation message
    # Domain logic will be implemented in Prompt 6
    await telegram_service.send_confirmation_message(chat_id, f"Button pressed: {data}")


# Message sending is now handled by the TelegramService
