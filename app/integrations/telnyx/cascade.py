"""Call cascade orchestration for Telnyx integration."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.services import TelnyxService
from app.core.ui_strings import get_tts_string
from app.domain.panic import generate_idempotency_key
from app.storage.models import CallAttempt, Incident, MemberLink, User

logger = get_logger(__name__)


async def initiate_call_cascade(
    session: AsyncSession,
    incident_id: int,
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
) -> None:
    """
    Initiate call cascade for an incident.

    This starts parallel calls to all guardians with proper retry logic.
    """
    # Get active incident
    result = await session.execute(
        select(Incident).where(Incident.id == incident_id, Incident.status == "active")
    )
    incident = result.scalar_one_or_none()

    if not incident:
        logger.warning(
            "Cannot initiate call cascade - incident not found or not active",
            incident_id=incident_id,
            correlation_id=correlation_id,
        )
        return

    # Get active watchers ordered by priority
    result = await session.execute(
        select(MemberLink)
        .where(
            MemberLink.traveler_user_id == incident.traveler_user_id,
            MemberLink.status == "active",
            MemberLink.calls_enabled,
        )
        .order_by(MemberLink.created_at)
    )
    watchers = list(result.scalars().all())

    if not watchers:
        logger.warning(
            "No active watchers with calls enabled",
            incident_id=incident_id,
            correlation_id=correlation_id,
        )
        return

    # Get ward user for TTS message
    result = await session.execute(
        select(User).where(User.id == incident.traveler_user_id)
    )
    ward = result.scalar_one()

    # Start parallel calls to all guardians
    call_tasks = []
    for watcher_link in watchers:
        task = asyncio.create_task(
            initiate_call_to_guardian(
                session,
                incident,
                watcher_link,
                ward,
                telnyx_service,
                correlation_id,
            )
        )
        call_tasks.append(task)

    # Wait for all initial calls to complete
    await asyncio.gather(*call_tasks, return_exceptions=True)

    logger.info(
        "Call cascade initiated",
        incident_id=incident_id,
        watcher_count=len(watchers),
        correlation_id=correlation_id,
    )


async def initiate_call_to_guardian(
    session: AsyncSession,
    incident: Incident,
    watcher_link: MemberLink,
    ward: User,
    telnyx_service: TelnyxService,
    correlation_id: str | None = None,
    attempt_no: int = 1,
) -> None:
    """
    Initiate call to a specific guardian.

    This handles the call logic for a single guardian with retry logic.
    """
    # Get watcher user
    result = await session.execute(
        select(User).where(User.id == watcher_link.watcher_user_id)
    )
    watcher = result.scalar_one()

    if not watcher.phone_e164:
        logger.warning(
            "Watcher has no phone number",
            watcher_id=watcher.id,
            incident_id=incident.id,
            correlation_id=correlation_id,
        )
        return

    # Create call attempt record
    call_attempt = CallAttempt(
        alert_id=None,  # Will be set when we create the alert
        to_e164=watcher.phone_e164,
        attempt_no=attempt_no,
        started_at=datetime.now(UTC),
    )
    session.add(call_attempt)
    await session.flush()

    # Generate idempotency key
    idempotency_key = generate_idempotency_key(
        incident.id, "call", gid=watcher.id, attempt=attempt_no
    )

    # Create Telnyx call payload
    call_payload = create_call_payload(
        incident,
        watcher,
        ward,
        call_attempt.id,
        idempotency_key,
    )

    # Use the driver to initiate the call (real or simulated)
    from app.integrations.telnyx.driver import initiate_call

    success = await initiate_call(
        telnyx_service,
        call_payload,
        idempotency_key,
        correlation_id,
    )

    if not success:
        logger.error(
            "Failed to initiate call",
            call_attempt_id=call_attempt.id,
            watcher_id=watcher.id,
            correlation_id=correlation_id,
        )

    # TODO: Send call to Telnyx (will be implemented in Prompt 6)
    # await send_telnyx_call(call_payload)

    logger.info(
        "Call initiated to guardian",
        incident_id=incident.id,
        watcher_id=watcher.id,
        phone=watcher.phone_e164,
        attempt_no=attempt_no,
        call_attempt_id=call_attempt.id,
        correlation_id=correlation_id,
    )


def create_call_payload(
    incident: Incident,
    watcher: User,
    ward: User,
    call_attempt_id: int,
    idempotency_key: str,
) -> dict[str, Any]:
    """
    Create Telnyx call payload with Russian TTS.

    This creates a call that plays TTS message and gathers DTMF input.
    """
    # Create TTS message
    tts_message = get_tts_string("panic_message", name=ward.display_name)

    # Create gather action for DTMF
    gather_action = {
        "type": "gather",
        "input": ["dtmf"],
        "timeout_ms": settings.CALL_RING_TIMEOUT_SEC * 1000,
        "max_digits": 1,
        "valid_digits": ["1"],
        "action_on_empty_result": {"type": "hangup"},
    }

    # Create speak action
    speak_action = {
        "type": "speak",
        "payload": tts_message,
        "voice": "female",
        "language": "ru-RU",
        "payload_type": "text",
    }

    # Create call payload
    payload = {
        "to": [watcher.phone_e164],
        "from": settings.TELNYX_CONNECTION_ID,
        "connection_id": settings.TELNYX_CONNECTION_ID,
        "webhook_url": f"{settings.BASE_URL}/telnyx/webhook",
        "webhook_failover_url": f"{settings.BASE_URL}/telnyx/webhook",
        "client_state": {
            "incident_id": incident.id,
            "watcher_id": watcher.id,
            "call_attempt_id": call_attempt_id,
            "idempotency_key": idempotency_key,
        },
        "actions": [
            speak_action,
            speak_action,  # Play twice as specified
            gather_action,
        ],
    }

    return payload


async def handle_call_answered(
    session: AsyncSession,
    call_control_id: str,
    incident_id: int,
    watcher_id: int,
    call_attempt_id: int,
    correlation_id: str | None = None,
) -> None:
    """
    Handle call answered event.

    This is called when a call is answered and TTS starts playing.
    """
    # Update call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.id == call_attempt_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt:
        call_attempt.result = "answered"
        call_attempt.ended_at = datetime.now(UTC)

    logger.info(
        "Call answered",
        call_control_id=call_control_id,
        incident_id=incident_id,
        watcher_id=watcher_id,
        call_attempt_id=call_attempt_id,
        correlation_id=correlation_id,
    )


async def handle_call_hangup(
    session: AsyncSession,
    call_control_id: str,
    incident_id: int,
    watcher_id: int,
    call_attempt_id: int,
    hangup_cause: str,
    correlation_id: str | None = None,
) -> None:
    """
    Handle call hangup event.

    This determines if we need to retry the call based on the hangup cause.
    """
    # Update call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.id == call_attempt_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt:
        call_attempt.result = map_hangup_cause_to_result(hangup_cause)
        call_attempt.ended_at = datetime.now(UTC)

    # Determine if we should retry
    should_retry = should_retry_call(
        hangup_cause, call_attempt.attempt_no if call_attempt else 1
    )

    if should_retry:
        await schedule_call_retry(
            session,
            incident_id,
            watcher_id,
            call_attempt_id,
            correlation_id,
        )

    logger.info(
        "Call hung up",
        call_control_id=call_control_id,
        incident_id=incident_id,
        watcher_id=watcher_id,
        call_attempt_id=call_attempt_id,
        hangup_cause=hangup_cause,
        should_retry=should_retry,
        correlation_id=correlation_id,
    )


async def handle_dtmf_gather(
    session: AsyncSession,
    call_control_id: str,
    incident_id: int,
    watcher_id: int,
    call_attempt_id: int,
    digits: str,
    correlation_id: str | None = None,
) -> None:
    """
    Handle DTMF gather event.

    This processes the DTMF input from the guardian.
    """
    # Update call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.id == call_attempt_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt:
        call_attempt.dtmf_received = digits
        call_attempt.result = "answered"
        call_attempt.ended_at = datetime.now(UTC)

    # Process DTMF input
    if digits == "1":
        # Guardian acknowledged the incident
        await acknowledge_incident_via_call(
            session,
            incident_id,
            watcher_id,
            correlation_id,
        )
    else:
        # Invalid input, hang up
        logger.info(
            "Invalid DTMF input",
            call_control_id=call_control_id,
            incident_id=incident_id,
            watcher_id=watcher_id,
            digits=digits,
            correlation_id=correlation_id,
        )

    # TODO: Send acknowledgment TTS and hang up (will be implemented in Prompt 6)
    # await send_acknowledgment_tts(call_control_id)


async def acknowledge_incident_via_call(
    session: AsyncSession,
    incident_id: int,
    watcher_id: int,
    correlation_id: str | None = None,
) -> None:
    """
    Acknowledge incident via call (DTMF "1").

    This stops all retries and hangs up calls.
    """
    from app.domain.panic import acknowledge_panic

    # Acknowledge the incident
    success = await acknowledge_panic(
        session,
        incident_id,
        watcher_id,
        correlation_id,
    )

    if success:
        logger.info(
            "Incident acknowledged via call",
            incident_id=incident_id,
            watcher_id=watcher_id,
            correlation_id=correlation_id,
        )

        # TODO: Send acknowledgment TTS to all active calls (will be implemented in Prompt 6)
        # await send_acknowledgment_to_all_calls(incident_id)
    else:
        logger.warning(
            "Failed to acknowledge incident via call",
            incident_id=incident_id,
            watcher_id=watcher_id,
            correlation_id=correlation_id,
        )


def map_hangup_cause_to_result(hangup_cause: str) -> str:
    """Map Telnyx hangup cause to our result format."""
    cause_mapping = {
        "call_rejected": "failed",
        "busy": "busy",
        "no_answer": "no_answer",
        "call_timeout": "no_answer",
        "call_canceled": "failed",
        "call_failed": "failed",
    }
    return cause_mapping.get(hangup_cause, "failed")


def should_retry_call(hangup_cause: str, attempt_no: int) -> bool:
    """
    Determine if we should retry a call based on hangup cause and attempt number.

    Retry conditions:
    - hangup_cause indicates retryable failure (busy, no_answer)
    - attempt_no < CALL_MAX_RETRIES
    """
    retryable_causes = ["busy", "no_answer", "call_timeout"]

    return hangup_cause in retryable_causes and attempt_no < settings.CALL_MAX_RETRIES


async def schedule_call_retry(
    session: AsyncSession,
    incident_id: int,
    watcher_id: int,
    call_attempt_id: int,
    correlation_id: str | None = None,
) -> None:
    """
    Schedule a call retry with staggered timing.

    Retries are staggered based on guardian priority and attempt number.
    """
    # Get the call attempt to determine next attempt number
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.id == call_attempt_id)
    )
    call_attempt = result.scalar_one_or_none()

    if not call_attempt:
        return

    next_attempt_no = call_attempt.attempt_no + 1

    # Calculate retry delay (staggered based on priority)
    base_delay = settings.PANIC_RETRY_INTERVAL_SEC
    priority_multiplier = 1.0  # Could be based on guardian priority

    retry_delay = base_delay * priority_multiplier

    # Schedule retry
    retry_time = datetime.now(UTC) + timedelta(seconds=retry_delay)

    # TODO: Schedule retry job (will be implemented in Prompt 6)
    # await schedule_action(
    #     incident_id,
    #     "call_retry",
    #     retry_time,
    #     {
    #         "watcher_id": watcher_id,
    #         "attempt_no": next_attempt_no,
    #         "original_call_attempt_id": call_attempt_id,
    #     }
    # )

    logger.info(
        "Scheduled call retry",
        incident_id=incident_id,
        watcher_id=watcher_id,
        call_attempt_id=call_attempt_id,
        next_attempt_no=next_attempt_no,
        retry_delay=retry_delay,
        retry_time=retry_time,
        correlation_id=correlation_id,
    )


async def handle_call_retry(
    session: AsyncSession,
    incident_id: int,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> None:
    """
    Handle scheduled call retry.

    This is called by the scheduler to retry a failed call.
    """
    watcher_id = payload.get("watcher_id")
    attempt_no = payload.get("attempt_no", 1)

    if not watcher_id:
        logger.error("Missing watcher_id for call retry")
        return

    # Get incident and watcher
    result = await session.execute(
        select(Incident).where(Incident.id == incident_id, Incident.status == "active")
    )
    incident = result.scalar_one_or_none()

    if not incident:
        logger.info("Incident no longer active, skipping retry")
        return

    result = await session.execute(
        select(MemberLink).where(
            MemberLink.watcher_user_id == watcher_id,
            MemberLink.traveler_user_id == incident.traveler_user_id,
            MemberLink.status == "active",
            MemberLink.calls_enabled,
        )
    )
    watcher_link = result.scalar_one_or_none()

    if not watcher_link:
        logger.warning("Watcher link not found for retry")
        return

    result = await session.execute(
        select(User).where(User.id == incident.traveler_user_id)
    )
    ward = result.scalar_one()

    # Initiate retry call
    from app.core.dependencies import get_telnyx_service

    telnyx_service = get_telnyx_service(session)
    await initiate_call_to_guardian(
        session,
        incident,
        watcher_link,
        ward,
        telnyx_service,
        correlation_id,
        attempt_no=attempt_no,
    )
