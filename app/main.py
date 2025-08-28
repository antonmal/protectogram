"""Main FastAPI application factory."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api import admin, health, telegram, telnyx
from app.core.config import settings
from app.core.logging import setup_logging
from app.scheduler.setup import setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()

    # Conditional database and scheduler setup
    if settings.ENABLE_DB:
        from app.core.database import init_db

        await init_db()

    if settings.SCHEDULER_ENABLED:
        await setup_scheduler()

    yield
    # Shutdown
    # Cleanup will be handled by FastAPI


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Protectogram",
        description="Telegram + Telnyx safety assistant - Panic Button v1",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
    app.include_router(telnyx.router, prefix="/telnyx", tags=["telnyx"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    # Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    return app


app = create_app()


def main() -> None:
    """Main entry point for the application."""
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104: binding for local dev only; prod runs behind Fly proxy
        port=port,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
