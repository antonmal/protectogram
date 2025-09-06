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

    # Initialize communication manager (temporarily disabled for testing)
    # from app.core.communications import CommunicationManager
    # app.state.communication_manager = CommunicationManager(app.state.settings)
    app.state.communication_manager = None

    # Initialize Telegram client
    from app.integrations.telegram_client import TelegramClient

    telegram_client = TelegramClient(app.state.settings)
    app.state.telegram_client = telegram_client

    # Initialize Telegram bot asynchronously
    await telegram_client.initialize_application()

    if telegram_client.is_ready():
        print("✅ Telegram bot initialized successfully")
    else:
        print("⚠️ Telegram bot initialization failed - continuing without Telegram")

    print("✅ Protectogram application ready")

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


# Environment-specific app factory functions for deployment
def create_staging_app() -> FastAPI:
    """Create staging app instance."""
    from app.config.settings import SettingsFactory

    settings = SettingsFactory.create("staging")
    return create_app(settings)


def create_production_app() -> FastAPI:
    """Create production app instance."""
    from app.config.settings import SettingsFactory

    settings = SettingsFactory.create("production")
    return create_app(settings)


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

    # Include API routers
    from app.api import api_router, webhook_router

    app.include_router(api_router)
    app.include_router(webhook_router)
    # app.include_router(twilio.router, prefix="/webhooks/twilio", tags=["webhooks"])

    # Include admin router (available in all environments with proper auth)
    from app.api.admin import admin_router

    app.include_router(admin_router, prefix="/api")


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
