"""API package initialization."""

from fastapi import APIRouter

from app.api.v1 import v1_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include version routers
api_router.include_router(v1_router)
