"""Admin endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
async def admin_status() -> dict[str, str]:
    """Admin status endpoint."""
    # TODO: Implement admin status endpoint
    return {"status": "not_implemented"}
