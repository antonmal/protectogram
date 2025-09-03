"""
FastAPI dependencies for Protectogram v3.1.
Provides dependency injection for settings, database, and services.
"""

from typing import Annotated, AsyncGenerator
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import BaseAppSettings
from app.database import get_async_db
from app.services.guardian import GuardianService
from app.services.user import UserService
from app.services.user_guardian import UserGuardianService
from app.services.telegram_onboarding import TelegramOnboardingService


def get_settings(request: Request) -> BaseAppSettings:
    """
    Get application settings from request state.

    Args:
        request: FastAPI request object.

    Returns:
        Environment-specific settings instance.
    """
    return request.app.state.settings


async def get_database(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session with proper cleanup.

    Args:
        request: FastAPI request object.

    Yields:
        SQLAlchemy async database session.
    """
    async for session in get_async_db():
        yield session


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


def get_telegram_onboarding_service(
    db: Annotated[AsyncSession, Depends(get_database)],
) -> TelegramOnboardingService:
    """
    Get Telegram onboarding service with all required services injected.

    Returns:
        TelegramOnboardingService instance.
    """
    user_service = UserService(db=db)
    guardian_service = GuardianService(db=db)
    user_guardian_service = UserGuardianService(db=db)

    return TelegramOnboardingService(
        db=db,
        user_service=user_service,
        guardian_service=guardian_service,
        user_guardian_service=user_guardian_service,
    )


# Service dependencies with proper injection
def get_user_service(
    db: Annotated[AsyncSession, Depends(get_database)],
) -> UserService:
    """
    Get user service with database session injected.

    Returns:
        User service instance.
    """
    return UserService(db=db)


def get_guardian_service(
    db: Annotated[AsyncSession, Depends(get_database)],
) -> GuardianService:
    """
    Get guardian service with database session injected.

    Returns:
        Guardian service instance.
    """
    return GuardianService(db=db)


def get_user_guardian_service(
    db: Annotated[AsyncSession, Depends(get_database)],
) -> UserGuardianService:
    """
    Get user guardian service with database session injected.

    Returns:
        User guardian service instance.
    """
    return UserGuardianService(db=db)


def get_panic_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_database)],
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
    db: Annotated[AsyncSession, Depends(get_database)],
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


def get_notification_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_database)],
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
DatabaseDep = Annotated[AsyncSession, Depends(get_database)]
CommunicationDep = Annotated[object, Depends(get_communication_manager)]
TelegramDep = Annotated[object, Depends(get_telegram_client)]
PanicServiceDep = Annotated[object, Depends(get_panic_service)]
TripServiceDep = Annotated[object, Depends(get_trip_service)]
GuardianServiceDep = Annotated[object, Depends(get_guardian_service)]
NotificationServiceDep = Annotated[object, Depends(get_notification_service)]
