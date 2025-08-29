"""Health check endpoints."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe endpoint."""
    # TODO: Check database connectivity, external services, etc.
    # For now, return 503 to indicate the service is starting up
    raise HTTPException(
        status_code=503,
        detail={"status": "starting"},
    )
