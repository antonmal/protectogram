"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.users import router as users_router

# Create main v1 router
v1_router = APIRouter(prefix="/v1")

# Include sub-routers
v1_router.include_router(users_router)
