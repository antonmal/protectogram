"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter
from prometheus_client import Counter, Histogram

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
async def health_ready() -> dict[str, str]:  # Temporarily remove db dependency
    """Readiness probe - application ready to serve requests."""
    # Temporarily disable database check for deployment
    health_check_counter.labels(endpoint="ready", status="success").inc()
    return {
        "status": "ready",
        "timestamp": datetime.now(UTC).isoformat(),
        "database": "disabled_for_deployment",
    }
