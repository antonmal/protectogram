"""Job handlers for scheduled actions."""

from datetime import UTC, datetime
from typing import Any

from app.core.database import get_session_factory
from app.core.logging import get_logger
from app.core.metrics import scheduler_job_lag

logger = get_logger(__name__)


async def handle_scheduled_action(
    incident_id: int,
    action_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Handle a scheduled action for an incident."""
    start_time = datetime.now(UTC)

    logger.info(
        "Executing scheduled action",
        incident_id=incident_id,
        action_type=action_type,
        payload=payload,
    )

    try:
        async with get_session_factory()() as session:
            if action_type == "panic_reminder":
                # TODO: Implement panic reminder logic
                logger.info(
                    "Panic reminder action (not yet implemented)",
                    incident_id=incident_id,
                    payload=payload,
                )
            elif action_type == "call_retry":
                from app.integrations.telnyx.cascade import handle_call_retry

                if payload is not None:
                    await handle_call_retry(session, incident_id, payload)
                else:
                    logger.warning(
                        "Call retry payload is None", incident_id=incident_id
                    )
            else:
                logger.warning(
                    "Unknown action type",
                    action_type=action_type,
                    incident_id=incident_id,
                )

        # Record job lag metric
        lag_seconds = (datetime.now(UTC) - start_time).total_seconds()
        scheduler_job_lag.labels(job_type=action_type).observe(lag_seconds)

        logger.info(
            "Scheduled action completed",
            incident_id=incident_id,
            action_type=action_type,
            duration_seconds=lag_seconds,
        )

    except Exception as e:
        logger.error(
            "Scheduled action failed",
            incident_id=incident_id,
            action_type=action_type,
            error=str(e),
        )
        raise
