"""Telnyx webhook endpoint."""

import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.idempotency import (
    generate_correlation_id,
    is_duplicate_inbox_event,
    store_inbox_event,
)
from app.core.logging import get_logger, log_with_context
from app.integrations.telnyx.call_control import handle_telnyx_event

router = APIRouter()

logger = get_logger(__name__)


def verify_telnyx_signature(
    payload: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """Verify Telnyx webhook signature."""
    expected_signature = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@router.post("/webhook")
async def telnyx_webhook(
    request: Request,
    telnyx_signature_ed25519: str = Header(..., alias="Telnyx-Signature-Ed25519"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle Telnyx webhook with signature verification and idempotency."""
    from app.core.config import settings

    # Read request body
    body = await request.body()

    # Verify signature
    if not verify_telnyx_signature(
        body, telnyx_signature_ed25519, settings.TELNYX_API_KEY
    ):
        get_logger(__name__).warning("Invalid Telnyx signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse JSON payload
    try:
        event_data = await request.json()
    except Exception as e:
        get_logger(__name__).error("Failed to parse Telnyx webhook body", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    # Generate correlation ID for tracing
    correlation_id = generate_correlation_id()
    logger = log_with_context(get_logger(__name__), correlation_id=correlation_id)

    # Extract event ID for idempotency
    event_id = event_data.get("data", {}).get("id", "")
    if not event_id:
        logger.error("Missing event ID in Telnyx webhook")
        raise HTTPException(status_code=400, detail="Missing event ID")

    # Check for duplicate event
    if await is_duplicate_inbox_event(db, "telnyx", event_id):
        logger.info("Duplicate Telnyx event ignored", event_id=event_id)
        return {"status": "ok", "message": "Duplicate event ignored"}

    try:
        # Store inbox event for idempotency
        await store_inbox_event(db, "telnyx", event_id, event_data)

        # Process the event
        await handle_telnyx_event(event_data, db, correlation_id)

        logger.info("Telnyx webhook processed successfully", event_id=event_id)
        return {"status": "ok", "message": "Event processed"}

    except Exception as e:
        logger.error(
            "Failed to process Telnyx webhook",
            event_id=event_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
