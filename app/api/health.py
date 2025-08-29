"""Health check endpoints."""

from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Health check endpoint for liveness probe."""
    return {"status": "live"}


@router.get("/health/ready")
def health_ready() -> Response:
    """Health check endpoint for readiness probe."""
    return Response(
        content='{"status": "not_ready"}',
        media_type="application/json",
        status_code=503,
    )
