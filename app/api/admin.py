"""Admin endpoints for testing and monitoring."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_telnyx_service
from app.core.logging import get_logger
from app.domain.panic import trigger_panic_test

router = APIRouter()

logger = get_logger(__name__)


@router.post("/trigger-panic-test")
async def trigger_panic_test_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Trigger a test panic incident (staging only)."""
    from app.core.config import settings

    if settings.is_production:
        raise HTTPException(status_code=403, detail="Not available in production")

    try:
        # Trigger test panic
        incident_id = await trigger_panic_test(db)

        logger.info("Test panic triggered", incident_id=incident_id)
        return {
            "status": "success",
            "message": "Test panic triggered",
            "incident_id": str(incident_id),
        }
    except Exception as e:
        logger.error("Failed to trigger test panic", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to trigger test panic"
        ) from e


class TelnyxSimulatorRequest(BaseModel):
    """Request model for Telnyx simulator."""

    incident_id: int
    guardian_user_id: int
    event_type: str
    digits: str | None = None


@router.post("/sim/telnyx")
async def telnyx_simulator_endpoint(
    request: TelnyxSimulatorRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Simulate Telnyx webhook events (staging only)."""
    from app.core.config import settings

    # Security check - only available in staging with test mode enabled
    if settings.is_production or not settings.TELNYX_WEBHOOK_TEST_MODE:
        raise HTTPException(
            status_code=403,
            detail="Simulator only available in staging with test mode enabled",
        )

    try:
        # Build simulated webhook event
        event_data = {
            "data": {
                "id": f"sim_{request.incident_id}_{request.guardian_user_id}",
                "event_type": request.event_type,
                "payload": {
                    "call_control_id": f"sim_call_{request.incident_id}_{request.guardian_user_id}",
                    "client_state": {
                        "incident_id": request.incident_id,
                        "watcher_id": request.guardian_user_id,
                        "call_attempt_id": 1,
                    },
                },
            }
        }

        # Add digits for DTMF events
        if request.event_type == "call.dtmf.received" and request.digits:
            event_data["data"]["payload"]["digits"] = request.digits  # type: ignore[index]

        # Process the simulated event
        telnyx_service = get_telnyx_service(db)
        await telnyx_service.process_telnyx_event(event_data)

        logger.info(
            "Telnyx event simulated",
            incident_id=request.incident_id,
            guardian_user_id=request.guardian_user_id,
            event_type=request.event_type,
            digits=request.digits,
        )

        return {"simulated": True}

    except Exception as e:
        logger.error(
            "Failed to simulate Telnyx event",
            error=str(e),
            incident_id=request.incident_id,
            guardian_user_id=request.guardian_user_id,
            event_type=request.event_type,
        )
        raise HTTPException(
            status_code=500, detail="Failed to simulate Telnyx event"
        ) from e
