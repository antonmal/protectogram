"""Telnyx webhook endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/webhook/telnyx", tags=["telnyx"])


@router.post("")
async def telnyx_webhook() -> dict[str, str]:
    """Telnyx webhook endpoint."""
    # TODO: Implement Telnyx webhook handling
    return {"status": "not_implemented"}
