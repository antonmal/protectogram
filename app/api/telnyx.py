"""Telnyx webhook endpoint."""

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.dependencies import TelnyxServiceDep
from app.core.idempotency import generate_correlation_id
from app.core.logging import get_logger, log_with_context
from app.integrations.telnyx.webhook import verify_webhook_signature, extract_webhook_data

router = APIRouter()

logger = get_logger(__name__)


@router.post("/webhook")
async def telnyx_webhook(
    request: Request,
    telnyx_service: TelnyxServiceDep,
    telnyx_signature_ed25519: str = Header(None, alias="Telnyx-Signature-Ed25519"),
    telnyx_timestamp: str = Header(None, alias="Telnyx-Timestamp"),
) -> dict[str, str]:
    """Handle Telnyx webhook with signature verification and idempotency."""
    from app.core.config import settings

    # Read request body
    body = await request.body()

    # Get all headers for verification
    headers = dict(request.headers)

    # Verify signature using new module with test mode support
    if not verify_webhook_signature(
        body, 
        telnyx_signature_ed25519 or "", 
        telnyx_timestamp or "",
        headers
    ):
        logger.warning("Invalid Telnyx webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Parse JSON payload
    try:
        event_data = await request.json()
    except Exception as e:
        logger.error("Failed to parse Telnyx webhook body", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    # Extract and validate webhook data
    webhook_data = extract_webhook_data(event_data, headers)
    if not webhook_data:
        logger.error("Invalid webhook data")
        raise HTTPException(status_code=400, detail="Invalid webhook data")

    # Generate correlation ID for tracing
    correlation_id = generate_correlation_id()
    logger = log_with_context(get_logger(__name__), correlation_id=correlation_id)

    # Extract event ID for idempotency
    event_id = webhook_data["event_id"]
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

        logger.info(
            "Telnyx webhook processed successfully", 
            event_id=event_id,
            event_type=webhook_data["event_type"],
            is_simulated=webhook_data["is_simulated"]
        )
        return {"status": "ok", "message": "Event processed"}

    except Exception as e:
        logger.error(
            "Failed to process Telnyx webhook",
            event_id=event_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
