"""API package initialization."""

from fastapi import APIRouter

from app.api.v1 import v1_router
from app.api.webhooks.telegram import router as telegram_webhook_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include version routers
api_router.include_router(v1_router)

# Include webhook routers (no /api prefix for webhooks)
webhook_router = APIRouter()
webhook_router.include_router(telegram_webhook_router)
