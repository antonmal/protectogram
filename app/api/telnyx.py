"""Telnyx webhook endpoint."""

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.dependencies import TelnyxServiceDep
from app.core.idempotency import generate_correlation_id
from app.core.logging import get_logger, log_with_context

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
    telnyx_service: TelnyxServiceDep,
    telnyx_signature_ed25519: str = Header(..., alias="Telnyx-Signature-Ed25519"),
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
    if await telnyx_service.is_duplicate_event("telnyx", event_id):
        logger.info("Duplicate Telnyx event ignored", event_id=event_id)
        return {"status": "ok", "message": "Duplicate event ignored"}

    try:
        # Store inbox event for idempotency
        await telnyx_service.store_inbox_event("telnyx", event_id, event_data)

        # Process the event
        await telnyx_service.process_telnyx_event(event_data, correlation_id)

        logger.info("Telnyx webhook processed successfully", event_id=event_id)
        return {"status": "ok", "message": "Event processed"}

    except Exception as e:
        logger.error(
            "Failed to process Telnyx webhook",
            event_id=event_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
