"""Prometheus metrics endpoint."""

from fastapi import APIRouter, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app.core.settings import settings

router = APIRouter()


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
