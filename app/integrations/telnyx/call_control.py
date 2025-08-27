"""Telnyx call control logic."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import call_attempts_total
from app.scheduler.setup import schedule_action
from app.storage.models import Alert, CallAttempt, MemberLink, User

logger = get_logger(__name__)


async def initiate_call_cascade(
    session: AsyncSession,
    alert_id: int,
    member_link: MemberLink,
    correlation_id: str | None = None,
    attempt_no: int = 1,
) -> None:
    """Initiate call cascade for a member link."""
    # Get user details
    result = await session.execute(
        select(User).where(User.id == member_link.watcher_user_id)
    )
    watcher = result.scalar_one_or_none()

    if not watcher or not watcher.phone_e164:
        logger.warning(
            "Watcher has no phone number",
            watcher_id=member_link.watcher_user_id,
        )
        return

    # Create call attempt record
    call_attempt = CallAttempt(
        alert_id=alert_id,
        to_e164=watcher.phone_e164,
        attempt_no=attempt_no,
        started_at=datetime.now(UTC),
    )
    session.add(call_attempt)
    await session.flush()

    try:
        # Initiate call via Telnyx
        telnyx_call_id = await create_telnyx_call(
            to_number=watcher.phone_e164,
            traveler_name=await get_traveler_name(
                session, member_link.traveler_user_id
            ),
            call_attempt_id=call_attempt.id,
            ring_timeout=member_link.ring_timeout_sec,
        )

        # Update call attempt with Telnyx call ID
        call_attempt.telnyx_call_id = telnyx_call_id

        # Schedule call timeout
        await schedule_action(
            member_link.traveler_user_id,  # Use incident_id for scheduling
            "call_timeout",
            datetime.now(UTC) + timedelta(seconds=member_link.ring_timeout_sec),
            {
                "call_attempt_id": call_attempt.id,
                "alert_id": alert_id,
                "member_link_id": member_link.id,
            },
        )

        call_attempts_total.labels(result="initiated").inc()

        logger.info(
            "Call initiated",
            call_attempt_id=call_attempt.id,
            telnyx_call_id=telnyx_call_id,
            to_number=watcher.phone_e164,
            correlation_id=correlation_id,
        )

    except Exception as e:
        call_attempt.result = "failed"
        call_attempt.error_code = str(e)
        call_attempt.ended_at = datetime.now(UTC)

        call_attempts_total.labels(result="failed").inc()

        logger.error(
            "Failed to initiate call",
            call_attempt_id=call_attempt.id,
            error=str(e),
            correlation_id=correlation_id,
        )


async def create_telnyx_call(
    to_number: str,
    traveler_name: str,
    call_attempt_id: int,
    ring_timeout: int,
) -> str:
    """Create a call via Telnyx Call Control API."""
    import telnyx

    telnyx.api_key = settings.TELNYX_API_KEY

    # Create call control call
    call = telnyx.Call.create(
        connection_id=settings.TELNYX_CONNECTION_ID,
        to=to_number,
        from_=settings.TELNYX_CONNECTION_ID,  # Use connection ID as from
        webhook_url=f"{settings.BASE_URL}/telnyx/webhook",
        webhook_failover_url=f"{settings.BASE_URL}/telnyx/webhook",
        timeout_secs=ring_timeout,
        client_state=f"call_attempt_{call_attempt_id}",
    )

    return call.id  # type: ignore[no-any-return]


async def get_traveler_name(session: AsyncSession, traveler_user_id: int) -> str:
    """Get traveler display name."""
    result = await session.execute(select(User).where(User.id == traveler_user_id))
    traveler = result.scalar_one_or_none()
    return traveler.display_name if traveler else "Unknown"


async def handle_telnyx_event(
    event_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle Telnyx webhook event."""
    event_type = event_data.get("event_type")
    call_id = event_data.get("data", {}).get("id")

    logger.info(
        "Received Telnyx event",
        event_type=event_type,
        call_id=call_id,
        correlation_id=correlation_id,
    )

    if event_type == "call.initiated":
        await handle_call_initiated(event_data, session, correlation_id)
    elif event_type == "call.answered":
        await handle_call_answered(event_data, session, correlation_id)
    elif event_type == "call.hangup":
        await handle_call_hangup(event_data, session, correlation_id)
    elif event_type == "call.dtmf.received":
        await handle_dtmf_received(event_data, session, correlation_id)
    else:
        logger.info("Unhandled Telnyx event", event_type=event_type)


async def handle_call_initiated(
    event_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle call initiated event."""
    call_id = event_data.get("data", {}).get("id")
    client_state = event_data.get("data", {}).get("client_state", "")

    if client_state.startswith("call_attempt_"):
        call_attempt_id = int(client_state.split("_")[2])

        # Update call attempt
        result = await session.execute(
            select(CallAttempt).where(CallAttempt.id == call_attempt_id)
        )
        call_attempt = result.scalar_one_or_none()

        if call_attempt:
            call_attempt.telnyx_call_id = call_id
            call_attempt.started_at = datetime.now(UTC)

            logger.info(
                "Call initiated",
                call_id=call_id,
                call_attempt_id=call_attempt_id,
                correlation_id=correlation_id,
            )


async def handle_call_answered(
    event_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle call answered event."""
    call_id = event_data.get("data", {}).get("id")

    # Find call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.telnyx_call_id == call_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt:
        call_attempt.result = "answered"
        call_attempt.ended_at = datetime.now(UTC)

        # Play TTS message
        await play_tts_message(session, call_id, call_attempt)

        call_attempts_total.labels(result="answered").inc()

        logger.info(
            "Call answered",
            call_id=call_id,
            call_attempt_id=call_attempt.id,
            correlation_id=correlation_id,
        )


async def handle_call_hangup(
    event_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle call hangup event."""
    call_id = event_data.get("data", {}).get("id")

    # Find call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.telnyx_call_id == call_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt and not call_attempt.result:
        # Determine result based on call duration
        if call_attempt.started_at:
            duration = (datetime.now(UTC) - call_attempt.started_at).total_seconds()
            if duration < 30:  # Short call, likely no answer
                call_attempt.result = "no_answer"
            else:
                call_attempt.result = "answered"

        call_attempt.ended_at = datetime.now(UTC)

        # Handle retry logic
        await handle_call_retry(session, call_attempt, correlation_id)

        logger.info(
            "Call ended",
            call_id=call_id,
            call_attempt_id=call_attempt.id,
            result=call_attempt.result,
            correlation_id=correlation_id,
        )


async def handle_dtmf_received(
    event_data: dict[str, Any],
    session: AsyncSession,
    correlation_id: str | None = None,
) -> None:
    """Handle DTMF received event."""
    call_id = event_data.get("data", {}).get("id")
    digits = event_data.get("data", {}).get("digits", "")

    # Find call attempt
    result = await session.execute(
        select(CallAttempt).where(CallAttempt.telnyx_call_id == call_id)
    )
    call_attempt = result.scalar_one_or_none()

    if call_attempt:
        call_attempt.dtmf_received = digits

        # Handle DTMF "1" for acknowledgment
        if digits == "1":
            await handle_dtmf_acknowledgment(session, call_attempt, correlation_id)

        logger.info(
            "DTMF received",
            call_id=call_id,
            digits=digits,
            call_attempt_id=call_attempt.id,
            correlation_id=correlation_id,
        )


async def play_tts_message(
    session: AsyncSession, call_id: str, call_attempt: CallAttempt
) -> None:
    """Play TTS message during call."""
    import telnyx

    telnyx.api_key = settings.TELNYX_API_KEY

    # Get traveler name
    result = await session.execute(
        select(User).join(Alert).where(Alert.id == call_attempt.alert_id)
    )
    traveler = result.scalar_one_or_none()
    traveler_name = traveler.display_name if traveler else "Unknown"

    # Create TTS message
    tts_text = (
        f"Тревога! Срочно свяжитесь с {traveler_name}. Нажмите 1, чтобы подтвердить."
    )

    # Play TTS
    telnyx.Call.control(
        call_id,
        actions=[
            {
                "action": "speak",
                "payload": {
                    "text": tts_text,
                    "language": "ru-RU",
                    "voice": "female",
                },
            }
        ],
    )


async def handle_dtmf_acknowledgment(
    session: AsyncSession,
    call_attempt: CallAttempt,
    correlation_id: str | None = None,
) -> None:
    """Handle DTMF acknowledgment."""
    # Get alert and incident
    result = await session.execute(
        select(Alert).where(Alert.id == call_attempt.alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert:
        # Acknowledge the incident
        from app.domain.panic import acknowledge_panic

        await acknowledge_panic(
            session,
            alert.incident_id,
            alert.audience_user_id,
            correlation_id,
        )

        # Hang up the call
        import telnyx

        telnyx.api_key = settings.TELNYX_API_KEY

        telnyx.Call.control(call_attempt.telnyx_call_id, actions=[{"action": "hangup"}])


async def handle_call_retry(
    session: AsyncSession,
    call_attempt: CallAttempt,
    correlation_id: str | None = None,
) -> None:
    """Handle call retry logic."""
    # Get alert and member link
    result = await session.execute(
        select(Alert).where(Alert.id == call_attempt.alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        return

    result = await session.execute(
        select(MemberLink).where(
            MemberLink.watcher_user_id == alert.audience_user_id,
            MemberLink.traveler_user_id == alert.incident.traveler_user_id,
        )
    )
    member_link = result.scalar_one_or_none()

    if not member_link:
        return

    # Check if we should retry
    if (
        call_attempt.result == "no_answer"
        and call_attempt.attempt_no < member_link.max_retries
    ):
        # Schedule retry
        retry_delay = member_link.retry_backoff_sec * call_attempt.attempt_no

        await schedule_action(
            alert.incident_id,
            "call_retry",
            datetime.now(UTC) + timedelta(seconds=retry_delay),
            {
                "alert_id": alert.id,
                "attempt_no": call_attempt.attempt_no + 1,
            },
        )

        logger.info(
            "Scheduled call retry",
            alert_id=alert.id,
            attempt_no=call_attempt.attempt_no + 1,
            retry_delay=retry_delay,
            correlation_id=correlation_id,
        )
