"""Telnyx outbound call driver with simulation support."""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import call_attempts_total
from app.core.services import TelnyxService

logger = get_logger(__name__)


async def initiate_call(
    telnyx_service: TelnyxService,
    payload: dict[str, Any],
    idempotency_key: str,
    correlation_id: str | None = None,
) -> bool:
    """
    Initiate a call via Telnyx or simulate it based on configuration.

    Args:
        telnyx_service: Telnyx service instance
        payload: Call payload for Telnyx API
        idempotency_key: Idempotency key for the call
        correlation_id: Correlation ID for tracing

    Returns:
        True if call was initiated (real or simulated), False otherwise
    """
    # Check if calls are enabled
    if not settings.CALLS_ENABLED or not settings.TELNYX_ENABLED:
        # Simulate the call
        await _simulate_call(telnyx_service, payload, idempotency_key, correlation_id)
        return True

    # Perform real call
    return await _perform_real_call(
        telnyx_service, payload, idempotency_key, correlation_id
    )


async def _simulate_call(
    telnyx_service: TelnyxService,
    payload: dict[str, Any],
    idempotency_key: str,
    correlation_id: str | None = None,
) -> None:
    """Simulate a call by storing it in outbox with simulated status."""
    from app.core.idempotency import mark_outbox_sent, store_outbox_message

    # Extract phone number for logging
    to_e164 = payload.get("to", "unknown")

    logger.info(
        "DRY-RUN telnyx: would dial",
        to_e164=to_e164,
        idempotency_key=idempotency_key[:8],
        correlation_id=correlation_id,
        mode="simulated",
    )

    # Store in outbox with simulated status
    outbox_message = await store_outbox_message(
        telnyx_service.get_session(),
        "telnyx",
        idempotency_key,
        payload,
    )

    # Mark as sent immediately (simulated)
    await mark_outbox_sent(
        telnyx_service.get_session(),
        outbox_message.id,
        "simulated",
    )

    # Increment metric
    call_attempts_total.labels(result="simulated").inc()

    logger.info(
        "Call simulated successfully",
        outbox_id=outbox_message.id,
        correlation_id=correlation_id,
        mode="simulated",
    )


async def _perform_real_call(
    telnyx_service: TelnyxService,
    payload: dict[str, Any],
    idempotency_key: str,
    correlation_id: str | None = None,
) -> bool:
    """Perform a real call via Telnyx API."""
    import httpx

    to_e164 = payload.get("to", "unknown")

    logger.info(
        "Initiating real Telnyx call",
        to_e164=to_e164,
        idempotency_key=idempotency_key[:8],
        correlation_id=correlation_id,
        mode="real",
    )

    try:
        # Make the actual Telnyx API call
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.telnyx.com/v2/calls",
                headers={
                    "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 201:
                call_data = response.json()
                call_id = call_data.get("data", {}).get("id")

                logger.info(
                    "Telnyx call initiated successfully",
                    call_id=call_id,
                    to_e164=to_e164,
                    correlation_id=correlation_id,
                    mode="real",
                )

                # Store in outbox and mark as sent
                from app.core.idempotency import mark_outbox_sent, store_outbox_message

                outbox_message = await store_outbox_message(
                    telnyx_service.get_session(),
                    "telnyx",
                    idempotency_key,
                    payload,
                )

                await mark_outbox_sent(
                    telnyx_service.get_session(),
                    outbox_message.id,
                    call_id,
                )

                call_attempts_total.labels(result="success").inc()
                return True
            else:
                logger.error(
                    "Telnyx API call failed",
                    status_code=response.status_code,
                    response_text=response.text,
                    to_e164=to_e164,
                    correlation_id=correlation_id,
                    mode="real",
                )

                call_attempts_total.labels(result="failed").inc()
                return False

    except Exception as e:
        logger.error(
            "Exception during Telnyx call",
            error=str(e),
            to_e164=to_e164,
            correlation_id=correlation_id,
            mode="real",
        )

        call_attempts_total.labels(result="failed").inc()
        return False
