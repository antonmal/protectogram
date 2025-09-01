"""Application factory for creating FastAPI instances."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional

from app.config.settings import BaseAppSettings, SettingsFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    print(f"Starting Protectogram in {app.state.settings.environment} mode")
    yield
    # Shutdown
    print("Shutting down Protectogram")


def create_app(settings: Optional[BaseAppSettings] = None) -> FastAPI:
    """
    Application factory with settings injection.

    Args:
        settings: Optional settings instance. If None, creates from environment.

    Returns:
        Configured FastAPI application instance.
    """

    if settings is None:
        settings = SettingsFactory.create()

    # Create FastAPI instance
    app = FastAPI(
        title=settings.app_name.title(),
        version="3.1.0",
        description="Personal safety application with panic button and trip tracking",
        lifespan=lifespan,
    )

    # Store settings in app state for dependency injection
    app.state.settings = settings

    # Configure middleware
    setup_middleware(app, settings)

    # Setup routes
    setup_routes(app, settings)

    # Setup error handlers
    setup_error_handlers(app, settings)

    return app


def setup_middleware(app: FastAPI, settings: BaseAppSettings):
    """Configure application middleware."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"]
        if settings.environment == "development"
        else ["https://protectogram.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_routes(app: FastAPI, settings: BaseAppSettings):
    """Configure application routes."""

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": settings.environment,
            "version": "3.1.0",
        }

    # API info endpoint
    @app.get("/")
    async def root():
        return {
            "app": settings.app_name,
            "version": "3.1.0",
            "environment": settings.environment,
            "docs": "/docs",
            "redoc": "/redoc",
        }

    # TODO: Add actual API routers
    # from app.api.v1 import panic, trips, guardians, users
    # app.include_router(panic.router, prefix="/api/v1/panic", tags=["panic"])
    # app.include_router(trips.router, prefix="/api/v1/trips", tags=["trips"])
    # app.include_router(guardians.router, prefix="/api/v1/guardians", tags=["guardians"])
    # app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

    # TODO: Add webhook routers
    # from app.api.webhooks import telegram, twilio
    # app.include_router(telegram.router, prefix="/webhooks/telegram", tags=["webhooks"])
    # app.include_router(twilio.router, prefix="/webhooks/twilio", tags=["webhooks"])


def setup_error_handlers(app: FastAPI, settings: BaseAppSettings):
    """Configure error handlers."""

    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(status_code=404, content={"detail": "Resource not found"})

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )
