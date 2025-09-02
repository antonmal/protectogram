"""Admin API router for administrative operations."""

from fastapi import APIRouter

from .migrations import router as migrations_router

# Create admin router with common prefix
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# Include all admin sub-routers
admin_router.include_router(migrations_router)
