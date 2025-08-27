"""Admin endpoints for testing and monitoring."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
