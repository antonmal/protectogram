"""Telegram message handlers."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.panic import (
    acknowledge_panic,
    cancel_panic,
    create_panic_incident,
    get_or_create_user,
    start_panic_cascade,
)

logger = get_logger(__name__)


async def handle_telegram_update(
    update_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle incoming Telegram update."""
    # Handle different update types
    if "message" in update_data:
        await handle_message(update_data["message"], session, correlation_id)
    elif "callback_query" in update_data:
        await handle_callback_query(
            update_data["callback_query"], session, correlation_id
        )
    else:
        logger.info("Unhandled update type", update_type=list(update_data.keys()))


async def handle_message(
    message: dict[str, Any],
    session: AsyncSession,
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
    user = await get_or_create_user(
        session,
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

    # Handle panic command
    if text.lower() in ["panic", "тревога", "паника"]:
        await handle_panic_command(session, user, correlation_id)
    elif text.lower() in ["cancel", "отмена", "отменить"]:
        await handle_cancel_command(session, user, correlation_id)
    else:
        # Send help message
        await send_help_message(chat_id)


async def handle_callback_query(
    callback_query: dict[str, Any],
    session: AsyncSession,
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
    user = await get_or_create_user(
        session,
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

    # Handle different callback types
    if data.startswith("ack_"):
        incident_id = int(data.split("_")[1])
        await handle_acknowledge_callback(session, user, incident_id, correlation_id)
    elif data.startswith("cancel_"):
        incident_id = int(data.split("_")[1])
        await handle_cancel_callback(session, user, incident_id, correlation_id)


async def handle_panic_command(
    session: AsyncSession,
    user: Any,
    correlation_id: str | None = None,
) -> None:
    """Handle panic button command."""
    # Create panic incident
    incident = await create_panic_incident(
        session,
        user.telegram_id,
        correlation_id,
    )

    # Start cascade
    await start_panic_cascade(session, incident, correlation_id)

    # Send confirmation to user
    await send_panic_confirmation(user.telegram_id, incident.id)


async def handle_cancel_command(
    session: AsyncSession,
    user: Any,
    correlation_id: str | None = None,
) -> None:
    """Handle cancel command."""
    # Find active incident for user
    from sqlalchemy import select

    from app.storage.models import Incident

    result = await session.execute(
        select(Incident).where(
            Incident.traveler_user_id == user.id,
            Incident.status == "active",
        )
    )
    incident = result.scalar_one_or_none()

    if incident:
        await cancel_panic(session, incident.id, user.id, correlation_id)
        await send_cancel_confirmation(user.telegram_id, incident.id)
    else:
        await send_no_active_incident_message(user.telegram_id)


async def handle_acknowledge_callback(
    session: AsyncSession,
    user: Any,
    incident_id: int,
    correlation_id: str | None = None,
) -> None:
    """Handle acknowledge button callback."""
    success = await acknowledge_panic(session, incident_id, user.id, correlation_id)

    if success:
        await send_acknowledgment_confirmation(user.telegram_id, incident_id)
    else:
        await send_acknowledgment_error(user.telegram_id, incident_id)


async def handle_cancel_callback(
    session: AsyncSession,
    user: Any,
    incident_id: int,
    correlation_id: str | None = None,
) -> None:
    """Handle cancel button callback."""
    success = await cancel_panic(session, incident_id, user.id, correlation_id)

    if success:
        await send_cancel_confirmation(user.telegram_id, incident_id)
    else:
        await send_cancel_error(user.telegram_id, incident_id)


# Message sending functions (implemented in outbox.py)
async def send_help_message(chat_id: int) -> None:
    """Send help message."""
    # This will be implemented in outbox.py
    pass


async def send_panic_confirmation(chat_id: int, incident_id: int) -> None:
    """Send panic confirmation message."""
    # This will be implemented in outbox.py
    pass


async def send_cancel_confirmation(chat_id: int, incident_id: int) -> None:
    """Send cancel confirmation message."""
    # This will be implemented in outbox.py
    pass


async def send_no_active_incident_message(chat_id: int) -> None:
    """Send no active incident message."""
    # This will be implemented in outbox.py
    pass


async def send_acknowledgment_confirmation(chat_id: int, incident_id: int) -> None:
    """Send acknowledgment confirmation message."""
    # This will be implemented in outbox.py
    pass


async def send_acknowledgment_error(chat_id: int, incident_id: int) -> None:
    """Send acknowledgment error message."""
    # This will be implemented in outbox.py
    pass


async def send_cancel_error(chat_id: int, incident_id: int) -> None:
    """Send cancel error message."""
    # This will be implemented in outbox.py
    pass
