"""FastAPI dependency injection for services."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.services import (
    DatabasePanicService,
    DatabaseTelegramService,
    DatabaseTelnyxService,
    PanicService,
    TelegramService,
    TelnyxService,
)


# Service dependencies
def get_telegram_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TelegramService:
    """Get Telegram service with database session."""
    return DatabaseTelegramService(session)


def get_panic_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PanicService:
    """Get Panic service with database session."""
    return DatabasePanicService(session)


def get_telnyx_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TelnyxService:
    """Get Telnyx service with database session."""
    return DatabaseTelnyxService(session)


# Type aliases for dependency injection
TelegramServiceDep = Annotated[TelegramService, Depends(get_telegram_service)]
PanicServiceDep = Annotated[PanicService, Depends(get_panic_service)]
TelnyxServiceDep = Annotated[TelnyxService, Depends(get_telnyx_service)]
