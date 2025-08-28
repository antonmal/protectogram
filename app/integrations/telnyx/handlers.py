"""Telnyx event handlers for Prompt 5 implementation."""

from typing import Any

from app.core.logging import get_logger
from app.core.services import TelnyxService

logger = get_logger(__name__)


async def handle_telnyx_event(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle Telnyx webhook event with service layer."""
    event_type = event_data.get("data", {}).get("event_type", "")
    event_id = event_data.get("data", {}).get("id", "")

    logger.info(
        "Processing Telnyx event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id,
    )

    # Process different event types
    if event_type == "call.initiated":
        await _handle_call_initiated(event_data, telnyx_service, correlation_id)
    elif event_type == "call.answered":
        await _handle_call_answered(event_data, telnyx_service, correlation_id)
    elif event_type == "call.hangup":
        await _handle_call_hangup(event_data, telnyx_service, correlation_id)
    elif event_type == "call.gather.ended":
        await _handle_call_gather_ended(event_data, telnyx_service, correlation_id)
    else:
        logger.info(
            "Unhandled Telnyx event type",
            event_type=event_type,
            event_id=event_id,
            correlation_id=correlation_id,
        )


async def _handle_call_initiated(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.initiated event."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")

    logger.info(
        "Call initiated",
        call_id=call_id,
        correlation_id=correlation_id,
    )

    # For Prompt 5: Just log the event
    # Call attempt creation will be handled in Prompt 6


async def _handle_call_answered(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.answered event."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")

    logger.info(
        "Call answered",
        call_id=call_id,
        correlation_id=correlation_id,
    )

    # For Prompt 5: Just log the event
    # TTS playback will be handled in Prompt 6


async def _handle_call_hangup(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.hangup event."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")
    hangup_cause = event_data.get("data", {}).get("payload", {}).get("hangup_cause", "")

    logger.info(
        "Call hung up",
        call_id=call_id,
        hangup_cause=hangup_cause,
        correlation_id=correlation_id,
    )

    # For Prompt 5: Just log the event
    # Call attempt completion will be handled in Prompt 6


async def _handle_call_gather_ended(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.gather.ended event (DTMF detection)."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")
    digits = event_data.get("data", {}).get("payload", {}).get("digits", "")

    logger.info(
        "Call gather ended",
        call_id=call_id,
        digits=digits,
        correlation_id=correlation_id,
    )

    # For Prompt 5: Just log the event
    # DTMF processing will be handled in Prompt 6
