"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from prometheus_client import Counter, Histogram
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger

router = APIRouter()

# Metrics
health_check_counter = Counter(
    "health_check_total",
    "Total number of health checks",
    ["endpoint", "status"],
)

health_check_duration = Histogram(
    "health_check_duration_seconds",
    "Health check duration in seconds",
    ["endpoint"],
)

logger = get_logger(__name__)


@router.get("/live")
async def health_live() -> dict[str, str]:
    """Liveness probe - basic application health."""
    health_check_counter.labels(endpoint="live", status="success").inc()
    return {"status": "alive", "timestamp": datetime.now(UTC).isoformat()}


@router.get("/ready")
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe - application ready to serve requests."""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        health_check_counter.labels(endpoint="ready", status="success").inc()
        return {
            "status": "ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        health_check_counter.labels(endpoint="ready", status="error").inc()
        return {
            "status": "not_ready",
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "disconnected",
            "error": str(e),
        }
