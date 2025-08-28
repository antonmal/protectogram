"""Panic incident domain logic."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import panic_acknowledged, panic_canceled, panic_incidents_started

# from app.integrations.telegram.outbox import send_telegram_alert  # Will be implemented in Prompt 6
from app.integrations.telnyx.call_control import initiate_call_cascade
from app.scheduler.setup import cancel_incident_jobs, schedule_action
from app.storage.models import Alert, Incident, MemberLink, User

logger = get_logger(__name__)


async def create_panic_incident(
    session: AsyncSession,
    traveler_telegram_id: str,
    correlation_id: str | None = None,
) -> Incident:
    """Create a new panic incident."""
    # Get or create traveler user
    traveler = await get_or_create_user(session, traveler_telegram_id)

    # Create incident
    incident = Incident(
        traveler_user_id=traveler.id,
        status="active",
    )
    session.add(incident)
    await session.flush()  # Get the ID

    logger.info(
        "Created panic incident",
        incident_id=incident.id,
        traveler_id=traveler.id,
        correlation_id=correlation_id,
    )

    # Increment metric
    panic_incidents_started.inc()

    return incident


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: str,
    display_name: str = "Unknown User",
) -> User:
    """Get or create a user by Telegram ID."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            display_name=display_name,
        )
        session.add(user)
        await session.flush()
        logger.info("Created new user", telegram_id=telegram_id)

    return user


async def get_active_watchers(
    session: AsyncSession,
    traveler_user_id: int,
) -> list[MemberLink]:
    """Get active watchers for a traveler."""
    result = await session.execute(
        select(MemberLink)
        .where(
            MemberLink.traveler_user_id == traveler_user_id,
            MemberLink.status == "active",
        )
        .order_by(MemberLink.call_priority)
    )
    return list(result.scalars().all())


async def start_panic_cascade(
    session: AsyncSession,
    incident: Incident,
    correlation_id: str | None = None,
) -> None:
    """Start the panic cascade for an incident."""
    # Get active watchers
    watchers = await get_active_watchers(session, incident.traveler_user_id)

    if not watchers:
        logger.warning(
            "No active watchers found",
            incident_id=incident.id,
            traveler_id=incident.traveler_user_id,
        )
        return

    # Create alerts for each watcher
    for watcher_link in watchers:
        # Telegram alert
        if watcher_link.telegram_enabled:
            alert = Alert(
                incident_id=incident.id,
                type="telegram",
                audience_user_id=watcher_link.watcher_user_id,
                status="pending",
            )
            session.add(alert)
            await session.flush()

            # Send Telegram alert (will be implemented in Prompt 6)
            # await send_telegram_alert(
            #     session,
            #     alert.id,
            #     watcher_link.watcher_user_id,
            #     incident.traveler_user_id,
            #     correlation_id,
            # )

        # Call alert
        if watcher_link.calls_enabled:
            alert = Alert(
                incident_id=incident.id,
                type="call",
                audience_user_id=watcher_link.watcher_user_id,
                status="pending",
            )
            session.add(alert)
            await session.flush()

            # Initiate call cascade
            await initiate_call_cascade(
                session,
                alert.id,
                watcher_link,
                correlation_id,
            )

    # Schedule reminder
    await schedule_action(
        incident.id,
        "panic_reminder",
        datetime.now(UTC) + timedelta(seconds=settings.DEFAULT_REMINDER_INTERVAL_SEC),
        {"reminder_count": 1},
    )

    logger.info(
        "Started panic cascade",
        incident_id=incident.id,
        watcher_count=len(watchers),
        correlation_id=correlation_id,
    )


async def acknowledge_panic(
    session: AsyncSession,
    incident_id: int,
    acknowledged_by_user_id: int,
    correlation_id: str | None = None,
) -> bool:
    """Acknowledge a panic incident."""
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident or incident.status != "active":
        logger.warning(
            "Cannot acknowledge incident - not found or not active",
            incident_id=incident_id,
            status=incident.status if incident else None,
        )
        return False

    # Update incident
    incident.status = "acknowledged"
    incident.acknowledged_by_user_id = acknowledged_by_user_id
    incident.ack_at = datetime.now(UTC)

    # Cancel scheduled jobs
    await cancel_incident_jobs(incident_id)

    # Increment metric
    panic_acknowledged.inc()

    logger.info(
        "Panic acknowledged",
        incident_id=incident_id,
        acknowledged_by=acknowledged_by_user_id,
        correlation_id=correlation_id,
    )

    return True


async def cancel_panic(
    session: AsyncSession,
    incident_id: int,
    canceled_by_user_id: int,
    correlation_id: str | None = None,
) -> bool:
    """Cancel a panic incident."""
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident or incident.status not in ["active", "acknowledged"]:
        logger.warning(
            "Cannot cancel incident - not found or already canceled",
            incident_id=incident_id,
            status=incident.status if incident else None,
        )
        return False

    # Update incident
    incident.status = "canceled"
    incident.canceled_at = datetime.now(UTC)

    # Cancel scheduled jobs
    await cancel_incident_jobs(incident_id)

    # Increment metric
    panic_canceled.inc()

    logger.info(
        "Panic canceled",
        incident_id=incident_id,
        canceled_by=canceled_by_user_id,
        correlation_id=correlation_id,
    )

    return True


async def send_panic_reminder(
    session: AsyncSession,
    incident_id: int,
    payload: dict | None = None,
) -> None:
    """Send a panic reminder."""
    reminder_count = payload.get("reminder_count", 1) if payload else 1

    # Check if incident is still active
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    if not incident or incident.status != "active":
        logger.info(
            "Skipping reminder - incident not active",
            incident_id=incident_id,
            status=incident.status if incident else None,
        )
        return

    # Get watchers and send reminders
    watchers = await get_active_watchers(session, incident.traveler_user_id)

    for watcher_link in watchers:
        if watcher_link.telegram_enabled:
            # Send Telegram alert (will be implemented in Prompt 6)
            # await send_telegram_alert(
            #     session,
            #     None,  # No specific alert ID for reminders
            #     watcher_link.watcher_user_id,
            #     incident.traveler_user_id,
            #     None,
            #     is_reminder=True,
            #     reminder_count=reminder_count,
            # )
            pass  # Placeholder for Prompt 6 implementation

    # Schedule next reminder if needed
    if reminder_count < 5:  # Max 5 reminders
        await schedule_action(
            incident_id,
            "panic_reminder",
            datetime.now(UTC)
            + timedelta(seconds=settings.DEFAULT_REMINDER_INTERVAL_SEC),
            {"reminder_count": reminder_count + 1},
        )


async def retry_call_attempt(
    session: AsyncSession,
    incident_id: int,
    payload: dict | None = None,
) -> None:
    """Retry a failed call attempt."""
    alert_id = payload.get("alert_id") if payload else None
    attempt_no = payload.get("attempt_no", 1) if payload else 1

    if not alert_id:
        logger.error("Missing alert_id for call retry")
        return

    # Get the alert
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        logger.error("Alert not found for retry", alert_id=alert_id)
        return

    # Get member link
    result = await session.execute(
        select(MemberLink).where(
            MemberLink.watcher_user_id == alert.audience_user_id,
            MemberLink.traveler_user_id == alert.incident.traveler_user_id,
        )
    )
    member_link = result.scalar_one_or_none()

    if not member_link:
        logger.error("Member link not found for retry", alert_id=alert_id)
        return

    # Retry the call
    await initiate_call_cascade(
        session,
        alert_id,
        member_link,
        None,
        attempt_no=attempt_no,
    )


async def trigger_panic_test(session: AsyncSession) -> str:
    """Trigger a test panic incident (for staging)."""
    # Create a test user if needed
    test_user = await get_or_create_user(
        session,
        "123456789",  # Test Telegram ID
        "Test User",
    )

    # Create test incident
    incident = await create_panic_incident(session, test_user.telegram_id)

    # Start cascade
    await start_panic_cascade(session, incident)

    return str(incident.id)
