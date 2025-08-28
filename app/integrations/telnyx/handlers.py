"""Telnyx event handlers for Prompt 6 implementation."""

from typing import Any

from app.core.logging import get_logger
from app.core.services import TelnyxService
from app.integrations.telnyx.cascade import (
    handle_call_answered,
    handle_call_hangup,
    handle_dtmf_gather,
)

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
    client_state = event_data.get("data", {}).get("payload", {}).get("client_state", {})

    logger.info(
        "Call initiated",
        call_id=call_id,
        client_state=client_state,
        correlation_id=correlation_id,
    )

    # Extract call attempt ID from client state
    call_attempt_id = client_state.get("call_attempt_id")
    if call_attempt_id:
        # Update call attempt with Telnyx call ID
        await telnyx_service.update_call_attempt(
            call_attempt_id, telnyx_call_id=call_id
        )


async def _handle_call_answered(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.answered event."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")
    client_state = event_data.get("data", {}).get("payload", {}).get("client_state", {})

    logger.info(
        "Call answered",
        call_id=call_id,
        client_state=client_state,
        correlation_id=correlation_id,
    )

    # Extract data from client state
    incident_id = client_state.get("incident_id")
    watcher_id = client_state.get("watcher_id")
    call_attempt_id = client_state.get("call_attempt_id")

    if incident_id and watcher_id and call_attempt_id:
        # Handle call answered via cascade module
        await handle_call_answered(
            telnyx_service.get_session(),
            call_id,
            incident_id,
            watcher_id,
            call_attempt_id,
            correlation_id,
        )


async def _handle_call_hangup(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.hangup event."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")
    hangup_cause = event_data.get("data", {}).get("payload", {}).get("hangup_cause", "")
    client_state = event_data.get("data", {}).get("payload", {}).get("client_state", {})

    logger.info(
        "Call hung up",
        call_id=call_id,
        hangup_cause=hangup_cause,
        client_state=client_state,
        correlation_id=correlation_id,
    )

    # Extract data from client state
    incident_id = client_state.get("incident_id")
    watcher_id = client_state.get("watcher_id")
    call_attempt_id = client_state.get("call_attempt_id")

    if incident_id and watcher_id and call_attempt_id:
        # Handle call hangup via cascade module
        await handle_call_hangup(
            telnyx_service.get_session(),
            call_id,
            incident_id,
            watcher_id,
            call_attempt_id,
            hangup_cause,
            correlation_id,
        )


async def _handle_call_gather_ended(
    event_data: dict[str, Any],
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """Handle call.gather.ended event (DTMF detection)."""
    call_id = event_data.get("data", {}).get("payload", {}).get("call_control_id", "")
    digits = event_data.get("data", {}).get("payload", {}).get("digits", "")
    client_state = event_data.get("data", {}).get("payload", {}).get("client_state", {})

    logger.info(
        "Call gather ended",
        call_id=call_id,
        digits=digits,
        client_state=client_state,
        correlation_id=correlation_id,
    )

    # Extract data from client state
    incident_id = client_state.get("incident_id")
    watcher_id = client_state.get("watcher_id")
    call_attempt_id = client_state.get("call_attempt_id")

    if incident_id and watcher_id and call_attempt_id:
        # Handle DTMF gather via cascade module
        await handle_dtmf_gather(
            telnyx_service.get_session(),
            call_id,
            incident_id,
            watcher_id,
            call_attempt_id,
            digits,
            correlation_id,
        )
