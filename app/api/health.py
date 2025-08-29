"""Health check endpoints."""

from fastapi import APIRouter, Response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, str]:
    """Liveness probe endpoint.

    Returns:
        dict: Status indicating the service is alive
    """
    return {"status": "live"}


@router.get("/ready")
async def health_ready() -> dict[str, str]:
    """Readiness probe endpoint.

    Returns:
        dict: Status indicating the service is not ready (stub implementation)
    """
    return Response(
        content='{"status": "not_ready"}', media_type="application/json", status_code=503
    )
