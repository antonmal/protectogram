"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.api import (
    admin_router,
    health_router,
    metrics_router,
    telegram_router,
    telnyx_router,
)
from app.core import install_middlewares, settings, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    # TODO: Initialize external services, load configurations, etc.
    yield
    # Shutdown
    # TODO: Cleanup resources, close connections, etc.


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
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

    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Include routers
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(telegram_router)
    app.include_router(telnyx_router)
    app.include_router(admin_router)

    return app


# Create the app instance
app = create_app()
