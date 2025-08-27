"""Telegram outbox for sending messages."""

from typing import Any

from sqlalchemy import select
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
from app.storage.models import User

logger = get_logger(__name__)


async def send_telegram_alert(
    session: AsyncSession,
    alert_id: int | None,
    watcher_user_id: int,
    traveler_user_id: int,
    correlation_id: str | None = None,
    is_reminder: bool = False,
    reminder_count: int = 1,
) -> None:
    """Send Telegram alert to watcher."""
    # Get user details
    result = await session.execute(select(User).where(User.id == watcher_user_id))
    watcher = result.scalar_one_or_none()

    result = await session.execute(select(User).where(User.id == traveler_user_id))
    traveler = result.scalar_one_or_none()

    if not watcher or not traveler:
        logger.error(
            "User not found", watcher_id=watcher_user_id, traveler_id=traveler_user_id
        )
        return

    # Create message payload
    if is_reminder:
        message_text = f"⚠️ Напоминание #{reminder_count}: Тревога от {traveler.display_name}! Нажмите «Я беру ответственность»."
    else:
        message_text = (
            f"🚨 ТРЕВОГА от {traveler.display_name}! Нажмите «Я беру ответственность»."
        )

    # Create inline keyboard
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Я беру ответственность",
                    "callback_data": f"ack_{alert_id}" if alert_id else "ack_general",
                }
            ],
            [
                {
                    "text": "Отменить тревогу",
                    "callback_data": f"cancel_{alert_id}"
                    if alert_id
                    else "cancel_general",
                }
            ],
        ]
    }

    payload = {
        "chat_id": watcher.telegram_id,
        "text": message_text,
        "reply_markup": keyboard,
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
            await mark_outbox_sent(session, outbox_message.id, "telegram_msg_id")  # type: ignore[arg-type]
            telegram_messages_sent.labels(message_type="alert").inc()

            logger.info(
                "Telegram alert sent",
                alert_id=alert_id,
                watcher_id=watcher_user_id,
                traveler_id=traveler_user_id,
                correlation_id=correlation_id,
            )
        else:
            await mark_outbox_failed(session, outbox_message.id, "Failed to send")  # type: ignore[arg-type]

    except Exception as e:
        logger.error(
            "Failed to send Telegram alert",
            alert_id=alert_id,
            watcher_id=watcher_user_id,
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


async def send_panic_confirmation(chat_id: int, incident_id: int) -> None:
    """Send panic confirmation message."""
    payload = {
        "chat_id": chat_id,
        "text": f"🚨 Тревога активирована! Инцидент #{incident_id}",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_cancel_confirmation(chat_id: int, incident_id: int) -> None:
    """Send cancel confirmation message."""
    payload = {
        "chat_id": chat_id,
        "text": f"✅ Тревога отменена. Инцидент #{incident_id}",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_no_active_incident_message(chat_id: int) -> None:
    """Send no active incident message."""
    payload = {
        "chat_id": chat_id,
        "text": "ℹ️ У вас нет активных тревог для отмены.",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_acknowledgment_confirmation(chat_id: int, incident_id: int) -> None:
    """Send acknowledgment confirmation message."""
    payload = {
        "chat_id": chat_id,
        "text": f"✅ Ответственность принята! Инцидент #{incident_id}",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_acknowledgment_error(chat_id: int, incident_id: int) -> None:
    """Send acknowledgment error message."""
    payload = {
        "chat_id": chat_id,
        "text": f"❌ Не удалось принять ответственность за инцидент #{incident_id}",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_cancel_error(chat_id: int, incident_id: int) -> None:
    """Send cancel error message."""
    payload = {
        "chat_id": chat_id,
        "text": f"❌ Не удалось отменить инцидент #{incident_id}",
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)


async def send_help_message(chat_id: int) -> None:
    """Send help message."""
    help_text = """
🤖 <b>Protectogram - Помощник безопасности</b>

<b>Команды:</b>
• <code>тревога</code> или <code>panic</code> - Активировать тревогу
• <code>отмена</code> или <code>cancel</code> - Отменить активную тревогу

<b>Кнопки:</b>
• <b>Я беру ответственность</b> - Подтвердить получение тревоги
• <b>Отменить тревогу</b> - Отменить активную тревогу

Для настройки свяжитесь с администратором.
    """.strip()

    payload = {
        "chat_id": chat_id,
        "text": help_text,
        "parse_mode": "HTML",
    }

    await send_telegram_message(payload)
