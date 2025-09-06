"""API v1 router configuration."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.guardians import router as guardians_router
from app.api.v1.user_guardians import router as user_guardians_router
from app.api.v1.users import router as users_router
from app.api.panic import router as panic_router

# Create main v1 router
v1_router = APIRouter(prefix="/v1")

# Include sub-routers
v1_router.include_router(auth_router)
v1_router.include_router(guardians_router)
v1_router.include_router(user_guardians_router)
v1_router.include_router(users_router)
v1_router.include_router(panic_router)
