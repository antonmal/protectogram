"""Telegram webhook endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.idempotency import (
    generate_correlation_id,
    is_duplicate_inbox_event,
    store_inbox_event,
)
from app.core.logging import get_logger, log_with_context
from app.integrations.telegram.handlers import handle_telegram_update

router = APIRouter()

logger = get_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    secret: str = Query(..., description="Webhook secret for validation"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle Telegram webhook with secret validation and idempotency."""
    from app.core.config import settings

    # Validate webhook secret
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        get_logger(__name__).warning(
            "Invalid webhook secret", secret_provided=secret[:8] + "..."
        )
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # Parse request body
    try:
        update_data = await request.json()
    except Exception as e:
        get_logger(__name__).error("Failed to parse webhook body", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    # Generate correlation ID for tracing
    correlation_id = generate_correlation_id()
    logger = log_with_context(get_logger(__name__), correlation_id=correlation_id)

    # Extract update_id for idempotency
    update_id = str(update_data.get("update_id", ""))
    if not update_id:
        logger.error("Missing update_id in Telegram update")
        raise HTTPException(status_code=400, detail="Missing update_id")

    # Check for duplicate event
    if await is_duplicate_inbox_event(db, "telegram", update_id):
        logger.info("Duplicate Telegram update ignored", update_id=update_id)
        return {"status": "ok", "message": "Duplicate update ignored"}

    try:
        # Store inbox event for idempotency
        await store_inbox_event(db, "telegram", update_id, update_data)

        # Process the update
        await handle_telegram_update(update_data, db, correlation_id)

        logger.info("Telegram webhook processed successfully", update_id=update_id)
        return {"status": "ok", "message": "Update processed"}

    except Exception as e:
        logger.error(
            "Failed to process Telegram webhook",
            update_id=update_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
