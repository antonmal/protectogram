"""API routers."""

from .admin import router as admin_router
from .health import router as health_router
from .metrics import router as metrics_router
from .telegram import router as telegram_router
from .telnyx import router as telnyx_router

__all__ = [
    "health_router",
    "metrics_router",
    "telegram_router",
    "telnyx_router",
    "admin_router",
]
