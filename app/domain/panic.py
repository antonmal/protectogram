"""Panic incident domain logic for Prompt 6 implementation."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.metrics import panic_acknowledged, panic_canceled, panic_incidents_started
from app.storage.models import Incident, MemberLink, User

logger = get_logger(__name__)


# Incident status constants
INCIDENT_STATUS_ACTIVE = "active"
INCIDENT_STATUS_ACKNOWLEDGED = "acknowledged"
INCIDENT_STATUS_CANCELED = "canceled"
INCIDENT_STATUS_EXHAUSTED = "exhausted"


def generate_idempotency_key(incident_id: int, action: str, **kwargs) -> str:
    """
    Generate idempotency key for outbound operations.

    Examples:
    - incident:{id}:telegram:guardian:{gid}:alert_initial
    - incident:{id}:call:{gid}:attempt:{n}
    - incident:{id}:telegram:ward:{type}
    """
    parts = [f"incident:{incident_id}", action]
    for key, value in kwargs.items():
        parts.append(f"{key}:{value}")
    return ":".join(parts)


async def create_panic_incident(
    session: AsyncSession,
    traveler_telegram_id: str,
    correlation_id: str | None = None,
) -> Incident | None:
    """
    Create a new panic incident.

    Returns None if user already has an active incident.
    """
    # Get or create traveler user
    traveler = await get_or_create_user(session, traveler_telegram_id)

    # Check if user already has an active incident
    result = await session.execute(
        select(Incident).where(
            Incident.traveler_user_id == traveler.id,
            Incident.status == INCIDENT_STATUS_ACTIVE,
        )
    )
    existing_incident = result.scalar_one_or_none()

    if existing_incident:
        logger.info(
            "User already has active incident",
            incident_id=existing_incident.id,
            traveler_id=traveler.id,
            correlation_id=correlation_id,
        )
        return existing_incident

    # Create new incident
    incident = Incident(
        traveler_user_id=traveler.id,
        status=INCIDENT_STATUS_ACTIVE,
    )
    session.add(incident)
    await session.flush()  # Get the ID

    logger.info(
        "Created new panic incident",
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
    """
    Get active watchers for a traveler, ordered by priority.

    Priority is determined by member_links.created_at (earlier = higher priority).
    """
    result = await session.execute(
        select(MemberLink)
        .where(
            MemberLink.traveler_user_id == traveler_user_id,
            MemberLink.status == "active",
        )
        .order_by(MemberLink.created_at)  # Earlier created = higher priority
    )
    return list(result.scalars().all())


# TODO: start_panic_cascade will be implemented in Prompt 6 with proper call cascade logic


async def acknowledge_panic(
    session: AsyncSession,
    incident_id: int,
    acknowledged_by_user_id: int,
    correlation_id: str | None = None,
) -> bool:
    """
    Acknowledge a panic incident.

    This stops retries and hangs up calls.
    """
    result = await session.execute(
        select(Incident).where(
            Incident.id == incident_id, Incident.status == INCIDENT_STATUS_ACTIVE
        )
    )
    incident = result.scalar_one_or_none()

    if not incident:
        logger.warning(
            "Cannot acknowledge incident - not found or not active",
            incident_id=incident_id,
            correlation_id=correlation_id,
        )
        return False

    # Update incident
    incident.status = INCIDENT_STATUS_ACKNOWLEDGED
    incident.acknowledged_by_user_id = acknowledged_by_user_id
    incident.ack_at = datetime.now(UTC)

    # TODO: Cancel scheduled jobs and hang up calls (will be implemented in Prompt 6)
    # await cancel_incident_jobs(incident_id)
    # await hang_up_all_calls(incident_id)

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
    """
    Cancel a panic incident.

    This stops jobs and calls.
    """
    result = await session.execute(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.status.in_([INCIDENT_STATUS_ACTIVE, INCIDENT_STATUS_ACKNOWLEDGED]),
        )
    )
    incident = result.scalar_one_or_none()

    if not incident:
        logger.warning(
            "Cannot cancel incident - not found or already canceled",
            incident_id=incident_id,
            correlation_id=correlation_id,
        )
        return False

    # Update incident
    incident.status = INCIDENT_STATUS_CANCELED
    incident.canceled_at = datetime.now(UTC)

    # TODO: Cancel scheduled jobs and hang up calls (will be implemented in Prompt 6)
    # await cancel_incident_jobs(incident_id)
    # await hang_up_all_calls(incident_id)

    # Increment metric
    panic_canceled.inc()

    logger.info(
        "Panic canceled",
        incident_id=incident_id,
        canceled_by=canceled_by_user_id,
        correlation_id=correlation_id,
    )

    return True


async def exhaust_incident(
    session: AsyncSession,
    incident_id: int,
    correlation_id: str | None = None,
) -> bool:
    """
    Mark incident as exhausted (no acknowledgment after retries).

    This is called when all retry attempts are exhausted.
    """
    result = await session.execute(
        select(Incident).where(
            Incident.id == incident_id, Incident.status == INCIDENT_STATUS_ACTIVE
        )
    )
    incident = result.scalar_one_or_none()

    if not incident:
        logger.warning(
            "Cannot exhaust incident - not found or not active",
            incident_id=incident_id,
            correlation_id=correlation_id,
        )
        return False

    # Update incident
    incident.status = INCIDENT_STATUS_EXHAUSTED
    incident.exhausted_at = datetime.now(UTC)

    logger.info(
        "Incident exhausted",
        incident_id=incident_id,
        correlation_id=correlation_id,
    )

    return True


async def get_incident_by_id(
    session: AsyncSession,
    incident_id: int,
) -> Incident | None:
    """Get incident by ID."""
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    return result.scalar_one_or_none()


async def get_active_incident_for_user(
    session: AsyncSession,
    traveler_user_id: int,
) -> Incident | None:
    """Get active incident for a user."""
    result = await session.execute(
        select(Incident).where(
            Incident.traveler_user_id == traveler_user_id,
            Incident.status == INCIDENT_STATUS_ACTIVE,
        )
    )
    return result.scalar_one_or_none()


async def trigger_panic_test(session: AsyncSession) -> str:
    """Trigger a test panic incident (for staging)."""
    # Create a test user if needed
    test_user = await get_or_create_user(
        session,
        "123456789",  # Test Telegram ID
        "Test User",
    )

    # Create test incident
    incident = await create_panic_incident(session, test_user.id)

    if incident:
        # TODO: Start cascade (will be implemented in Prompt 6)
        # await start_panic_cascade(session, incident)
        return str(incident.id)
    else:
        return "No new incident created (user already has active incident)"
