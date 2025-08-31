"""Telegram webhook router."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.integrations.telegram.client import TelegramClient
from app.integrations.telegram.inbound import compute_provider_event_id, process_inbound
from app.integrations.telegram.outbox import TelegramOutbox
from app.observability.metrics import duplicate_inbox_dropped_total
from app.storage.models import InboxEvent
from app.storage.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_telegram_client() -> TelegramClient:
    """Get Telegram client."""
    settings = Settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=500, detail="Telegram bot token not configured")
    
    return TelegramClient(
        bot_token=settings.telegram_bot_token,
        api_base=settings.telegram_api_base,
    )


async def get_telegram_outbox(
    client: TelegramClient = Depends(get_telegram_client),
) -> TelegramOutbox:
    """Get Telegram outbox."""
    return TelegramOutbox(client)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    outbox: TelegramOutbox = Depends(get_telegram_outbox),
) -> dict[str, Any]:
    """Handle Telegram webhook."""
    settings = Settings()
    
    # Validate webhook secret
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not settings.telegram_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    if not secret_token or secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    
    # Parse request body
    try:
        body = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook body", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e
    
    # Parse update
    try:
        from aiogram.types import Update
        update = Update.model_validate(body)
    except Exception as e:
        logger.error("Failed to parse Telegram update", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail="Invalid update format") from e
    
    # Compute provider event ID
    provider_event_id = compute_provider_event_id(update)
    
    # Log correlation info
    correlation_id = getattr(request.state, "correlation_id", "-")
    logger.info(
        "Processing Telegram webhook",
        extra={
            "correlation_id": correlation_id,
            "update_id": update.update_id,
            "provider_event_id": provider_event_id,
            "chat_id": extract_chat_id(update),
        },
    )
    
    # Try to insert inbox event for deduplication
    inbox_event = InboxEvent(
        provider="telegram",
        provider_event_id=provider_event_id,
        payload_json=body,
    )
    
    try:
        session.add(inbox_event)
        await session.commit()
    except Exception:
        # Duplicate event
        await session.rollback()
        duplicate_inbox_dropped_total.labels(provider="telegram").inc()
        
        logger.info(
            "Duplicate Telegram event dropped",
            extra={
                "correlation_id": correlation_id,
                "provider_event_id": provider_event_id,
            },
        )
        
        return {"ok": True}
    
    # Process inbound message
    try:
        result = await process_inbound(
            update=update,
            outbox=outbox,
            session=session,
            allowlist=settings.telegram_allowlist_chat_ids,
        )
        
        # Mark as processed
        inbox_event.processed_at = datetime.now()
        await session.commit()
        
        if result.processed:
            logger.info(
                "Telegram event processed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "provider_event_id": provider_event_id,
                    "message_type": result.message_type,
                    "chat_id": result.chat_id,
                },
            )
        else:
            logger.info(
                "Telegram event ignored (not in allowlist)",
                extra={
                    "correlation_id": correlation_id,
                    "provider_event_id": provider_event_id,
                    "chat_id": result.chat_id,
                },
            )
            
    except Exception as e:
        logger.error(
            "Failed to process Telegram event",
            extra={
                "correlation_id": correlation_id,
                "provider_event_id": provider_event_id,
                "error": str(e),
            },
        )
        # Don't raise - always return 200 to Telegram
    
    return {"ok": True}


def extract_chat_id(update: Any) -> int | None:
    """Extract chat ID from update."""
    if hasattr(update, 'message') and update.message:
        return update.message.chat.id
    elif (hasattr(update, 'callback_query') and update.callback_query 
          and update.callback_query.message):
        return update.callback_query.message.chat.id
    return None
