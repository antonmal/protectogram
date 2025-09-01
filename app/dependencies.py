"""
FastAPI dependencies for Protectogram v3.1.
Provides dependency injection for settings, database, and services.
"""

from typing import Annotated, Generator
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config.settings import BaseAppSettings
from app.database import get_database_session


def get_settings(request: Request) -> BaseAppSettings:
    """
    Get application settings from request state.

    Args:
        request: FastAPI request object.

    Returns:
        Environment-specific settings instance.
    """
    return request.app.state.settings


def get_database(request: Request) -> Generator[Session, None, None]:
    """
    Get database session with proper cleanup.

    Args:
        request: FastAPI request object.

    Yields:
        SQLAlchemy database session.
    """
    engine = request.app.state.engine
    session = get_database_session(engine)
    try:
        yield session
    finally:
        session.close()


def get_communication_manager(request: Request):
    """
    Get communication manager from application state.

    Args:
        request: FastAPI request object.

    Returns:
        Communication manager instance.
    """
    return request.app.state.communication_manager


def get_telegram_client(request: Request):
    """
    Get Telegram client from application state.

    Args:
        request: FastAPI request object.

    Returns:
        Telegram bot client instance.
    """
    return request.app.state.telegram_client


# Service dependencies with proper injection
def get_panic_service(
    request: Request,
    db: Annotated[Session, Depends(get_database)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    communication_manager=Depends(get_communication_manager),
    telegram_client=Depends(get_telegram_client),
):
    """
    Get panic service with all dependencies injected.

    Returns:
        Panic service instance with proper dependency injection.
    """
    from app.services.panic import PanicService

    return PanicService(
        db=db,
        settings=settings,
        communication_manager=communication_manager,
        telegram_client=telegram_client,
    )


def get_trip_service(
    request: Request,
    db: Annotated[Session, Depends(get_database)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    communication_manager=Depends(get_communication_manager),
    telegram_client=Depends(get_telegram_client),
):
    """
    Get trip service with all dependencies injected.

    Returns:
        Trip service instance with proper dependency injection.
    """
    from app.services.trip import TripService

    return TripService(
        db=db,
        settings=settings,
        communication_manager=communication_manager,
        telegram_client=telegram_client,
    )


def get_guardian_service(
    request: Request,
    db: Annotated[Session, Depends(get_database)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    communication_manager=Depends(get_communication_manager),
    telegram_client=Depends(get_telegram_client),
):
    """
    Get guardian service with all dependencies injected.

    Returns:
        Guardian service instance with proper dependency injection.
    """
    from app.services.guardian import GuardianService

    return GuardianService(
        db=db,
        settings=settings,
        communication_manager=communication_manager,
        telegram_client=telegram_client,
    )


def get_notification_service(
    request: Request,
    db: Annotated[Session, Depends(get_database)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
    communication_manager=Depends(get_communication_manager),
):
    """
    Get notification service with all dependencies injected.

    Returns:
        Notification service instance with proper dependency injection.
    """
    from app.services.notification import NotificationService

    return NotificationService(
        db=db, settings=settings, communication_manager=communication_manager
    )


# Type aliases for cleaner code
SettingsDep = Annotated[BaseAppSettings, Depends(get_settings)]
DatabaseDep = Annotated[Session, Depends(get_database)]
CommunicationDep = Annotated[object, Depends(get_communication_manager)]
TelegramDep = Annotated[object, Depends(get_telegram_client)]
PanicServiceDep = Annotated[object, Depends(get_panic_service)]
TripServiceDep = Annotated[object, Depends(get_trip_service)]
GuardianServiceDep = Annotated[object, Depends(get_guardian_service)]
NotificationServiceDep = Annotated[object, Depends(get_notification_service)]
