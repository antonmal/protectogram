"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    admin_router,
    health_router,
    metrics_router,
    telegram_router,
    telnyx_router,
)
from app.core import install_middlewares, setup_logging
from app.core.settings import get_settings
from app.scheduler.setup import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    settings = get_settings()

    # Startup
    if settings.scheduler_enabled:
        await start_scheduler()

    yield

    # Shutdown
    if settings.scheduler_enabled:
        await shutdown_scheduler()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title="Protectogram",
        description="Incident Management System",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
        lifespan=lifespan,
    )

    # Install middlewares in correct order
    install_middlewares(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(telegram_router, prefix="/telegram")
    app.include_router(telnyx_router)
    app.include_router(admin_router)

    return app


# Legacy compatibility - will be removed
app = create_app()
