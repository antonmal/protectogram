"""Telegram webhook endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/webhook/telegram", tags=["telegram"])


@router.post("")
async def telegram_webhook() -> dict[str, str]:
    """Telegram webhook endpoint."""
    # TODO: Implement Telegram webhook handling
    return {"status": "not_implemented"}
