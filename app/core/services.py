"""Service layer for business logic and data access."""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.storage.models import CallAttempt, InboxEvent, User

logger = get_logger(__name__)


class TelegramService(ABC):
    """Telegram service interface."""

    @abstractmethod
    async def get_or_create_user(self, telegram_id: str, display_name: str) -> User:
        """Get or create user by Telegram ID."""
        pass

    @abstractmethod
    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        """Store inbox event for deduplication."""
        pass

    @abstractmethod
    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        """Check if event is duplicate."""
        pass

    @abstractmethod
    async def send_confirmation_message(
        self, chat_id: int, message: str, correlation_id: str | None = None
    ) -> None:
        """Send confirmation message via Telegram."""
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Send message with optional reply markup via Telegram."""
        pass

    @property
    @abstractmethod
    def session(self) -> AsyncSession:
        """Get the database session."""
        pass


class PanicService(ABC):
    """Panic service interface."""

    @abstractmethod
    async def create_panic_incident(
        self, traveler_telegram_id: str, correlation_id: str | None = None
    ) -> str:
        """Create a new panic incident."""
        pass

    @abstractmethod
    async def acknowledge_panic(
        self,
        incident_id: int,
        acknowledged_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Acknowledge a panic incident."""
        pass

    @abstractmethod
    async def cancel_panic(
        self,
        incident_id: int,
        canceled_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Cancel a panic incident."""
        pass


class DatabaseTelegramService(TelegramService):
    """Database-backed Telegram service implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Get the database session."""
        return self._session

    async def get_or_create_user(self, telegram_id: str, display_name: str) -> User:
        """Get or create user by Telegram ID."""
        from sqlalchemy import select

        # Check if user exists
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user: User | None = result.scalar_one_or_none()

        if user:
            return user

        # Create new user
        new_user = User(
            telegram_id=telegram_id,
            display_name=display_name,
        )
        self._session.add(new_user)
        await self._session.flush()

        return new_user

    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        """Store inbox event for deduplication."""
        from app.core.idempotency import store_inbox_event

        return await store_inbox_event(self._session, provider, event_id, payload)

    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        """Check if event is duplicate."""
        from app.core.idempotency import is_duplicate_inbox_event

        return await is_duplicate_inbox_event(self._session, provider, event_id)

    async def send_confirmation_message(
        self, chat_id: int, message: str, correlation_id: str | None = None
    ) -> None:
        """Send confirmation message via Telegram."""
        from app.integrations.telegram.outbox import send_confirmation_message

        await send_confirmation_message(self._session, chat_id, message, correlation_id)

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Send message with optional reply markup via Telegram."""
        from app.integrations.telegram.outbox import send_telegram_message

        await send_telegram_message(
            self._session, chat_id, text, reply_markup, correlation_id
        )


class DatabasePanicService(PanicService):
    """Database-backed Panic service implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_panic_incident(
        self, traveler_telegram_id: str, correlation_id: str | None = None
    ) -> str:
        """Create a new panic incident."""
        from app.domain.panic import create_panic_incident as domain_create_incident

        incident = await domain_create_incident(
            self._session,
            traveler_telegram_id,
            correlation_id,
        )

        if incident:
            logger.info(
                "Panic incident created",
                incident_id=incident.id,
                traveler_telegram_id=traveler_telegram_id,
                correlation_id=correlation_id,
            )
            return str(incident.id)
        else:
            logger.warning(
                "Failed to create panic incident - active incident exists",
                traveler_telegram_id=traveler_telegram_id,
                correlation_id=correlation_id,
            )
            return ""

    async def acknowledge_panic(
        self,
        incident_id: int,
        acknowledged_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Acknowledge a panic incident."""
        from app.domain.panic import acknowledge_panic as domain_acknowledge

        success = await domain_acknowledge(
            self._session,
            incident_id,
            acknowledged_by_user_id,
            correlation_id,
        )

        if success:
            logger.info(
                "Panic incident acknowledged",
                incident_id=incident_id,
                acknowledged_by_user_id=acknowledged_by_user_id,
                correlation_id=correlation_id,
            )
        else:
            logger.warning(
                "Failed to acknowledge panic incident",
                incident_id=incident_id,
                acknowledged_by_user_id=acknowledged_by_user_id,
                correlation_id=correlation_id,
            )

        return success

    async def cancel_panic(
        self,
        incident_id: int,
        canceled_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Cancel a panic incident."""
        from app.domain.panic import cancel_panic as domain_cancel

        success = await domain_cancel(
            self._session,
            incident_id,
            canceled_by_user_id,
            correlation_id,
        )

        if success:
            logger.info(
                "Panic incident canceled",
                incident_id=incident_id,
                canceled_by_user_id=canceled_by_user_id,
                correlation_id=correlation_id,
            )
        else:
            logger.warning(
                "Failed to cancel panic incident",
                incident_id=incident_id,
                canceled_by_user_id=canceled_by_user_id,
                correlation_id=correlation_id,
            )

        return success


class FakeTelegramService(TelegramService):
    """In-memory fake Telegram service for contract tests."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.inbox_events: dict[str, InboxEvent] = {}
        self.sent_messages: list[dict[str, Any]] = []

    async def get_or_create_user(self, telegram_id: str, display_name: str) -> User:
        """Get or create user by Telegram ID."""
        if telegram_id not in self.users:
            user = User(
                id=len(self.users) + 1,
                telegram_id=telegram_id,
                display_name=display_name,
            )
            self.users[telegram_id] = user
        return self.users[telegram_id]

    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        """Store inbox event for deduplication."""
        event = InboxEvent(
            id=len(self.inbox_events) + 1,
            provider=provider,
            provider_event_id=event_id,
            payload_json=str(payload),
        )
        self.inbox_events[f"{provider}:{event_id}"] = event
        return event

    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        """Check if event is duplicate."""
        return f"{provider}:{event_id}" in self.inbox_events

    async def send_confirmation_message(
        self, chat_id: int, message: str, correlation_id: str | None = None
    ) -> None:
        """Send confirmation message via Telegram."""
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "message": message,
                "correlation_id": correlation_id,
            }
        )


class FakePanicService(PanicService):
    """In-memory fake Panic service for contract tests."""

    def __init__(self) -> None:
        self.incidents: dict[str, dict[str, Any]] = {}
        self.incident_counter = 0

    async def create_panic_incident(
        self, traveler_telegram_id: str, correlation_id: str | None = None
    ) -> str:
        """Create a new panic incident."""
        self.incident_counter += 1
        incident_id = str(self.incident_counter)
        self.incidents[incident_id] = {
            "traveler_telegram_id": traveler_telegram_id,
            "status": "active",
            "correlation_id": correlation_id,
        }
        return incident_id

    async def acknowledge_panic(
        self,
        incident_id: int,
        acknowledged_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Acknowledge a panic incident."""
        incident_key = str(incident_id)
        if incident_key in self.incidents:
            self.incidents[incident_key]["status"] = "acknowledged"
            self.incidents[incident_key]["acknowledged_by_user_id"] = (
                acknowledged_by_user_id
            )
            return True
        return False

    async def cancel_panic(
        self,
        incident_id: int,
        canceled_by_user_id: int,
        correlation_id: str | None = None,
    ) -> bool:
        """Cancel a panic incident."""
        incident_key = str(incident_id)
        if incident_key in self.incidents:
            self.incidents[incident_key]["status"] = "canceled"
            self.incidents[incident_key]["canceled_by_user_id"] = canceled_by_user_id
            return True
        return False


class TelnyxService(ABC):
    """Abstract interface for Telnyx operations."""

    @abstractmethod
    def get_session(self) -> AsyncSession:
        """Get the database session."""
        pass

    @abstractmethod
    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        pass

    @abstractmethod
    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        pass

    @abstractmethod
    async def process_telnyx_event(
        self, event_data: dict[str, Any], correlation_id: str | None = None
    ) -> None:
        pass

    @abstractmethod
    async def create_call_attempt(
        self, alert_id: int, to_e164: str, attempt_no: int = 1
    ) -> CallAttempt:
        pass

    @abstractmethod
    async def update_call_attempt(self, call_attempt_id: int, **kwargs: Any) -> None:
        pass


class DatabaseTelnyxService(TelnyxService):
    """Database-backed Telnyx service implementation."""

    def __init__(self, session: AsyncSession):
        self._session = session

    def get_session(self) -> AsyncSession:
        """Get the database session."""
        return self._session

    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        """Store inbox event for deduplication."""
        from app.core.idempotency import store_inbox_event

        return await store_inbox_event(self._session, provider, event_id, payload)

    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        """Check if event is duplicate."""
        from app.core.idempotency import is_duplicate_inbox_event

        return await is_duplicate_inbox_event(self._session, provider, event_id)

    async def process_telnyx_event(
        self, event_data: dict[str, Any], correlation_id: str | None = None
    ) -> None:
        """Process Telnyx webhook event."""
        from app.integrations.telnyx.handlers import handle_telnyx_event

        await handle_telnyx_event(event_data, self, correlation_id)

    async def create_call_attempt(
        self, alert_id: int, to_e164: str, attempt_no: int = 1
    ) -> CallAttempt:
        """Create a new call attempt record."""
        from datetime import UTC, datetime

        call_attempt = CallAttempt(
            alert_id=alert_id,
            to_e164=to_e164,
            attempt_no=attempt_no,
            started_at=datetime.now(UTC),
        )
        self._session.add(call_attempt)
        await self._session.flush()
        return call_attempt

    async def update_call_attempt(self, call_attempt_id: int, **kwargs: Any) -> None:
        """Update call attempt record."""
        from sqlalchemy import select

        result = await self._session.execute(
            select(CallAttempt).where(CallAttempt.id == call_attempt_id)
        )
        call_attempt = result.scalar_one_or_none()

        if call_attempt:
            for key, value in kwargs.items():
                if hasattr(call_attempt, key):
                    setattr(call_attempt, key, value)

            await self._session.flush()

            logger.info(
                "Call attempt updated",
                call_attempt_id=call_attempt_id,
                updates=kwargs,
            )
        else:
            logger.warning(
                "Call attempt not found for update",
                call_attempt_id=call_attempt_id,
            )


class FakeTelnyxService(TelnyxService):
    """In-memory fake Telnyx service for contract tests."""

    def __init__(self) -> None:
        self.inbox_events: dict[str, InboxEvent] = {}
        self.call_attempts: dict[int, CallAttempt] = {}
        self.processed_events: list[dict[str, Any]] = []
        self.call_attempt_counter = 0
        self._session: AsyncSession | None = None

    def get_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("Session not set for FakeTelnyxService")
        return self._session

    async def store_inbox_event(
        self, provider: str, event_id: str, payload: dict[str, Any]
    ) -> InboxEvent:
        """Store inbox event for deduplication."""
        event = InboxEvent(
            id=len(self.inbox_events) + 1,
            provider=provider,
            provider_event_id=event_id,
            payload_json=str(payload),
        )
        self.inbox_events[f"{provider}:{event_id}"] = event
        return event

    async def is_duplicate_event(self, provider: str, event_id: str) -> bool:
        """Check if event is duplicate."""
        return f"{provider}:{event_id}" in self.inbox_events

    async def process_telnyx_event(
        self, event_data: dict[str, Any], correlation_id: str | None = None
    ) -> None:
        """Process Telnyx webhook event."""
        self.processed_events.append(
            {
                "event_data": event_data,
                "correlation_id": correlation_id,
            }
        )

    async def create_call_attempt(
        self, alert_id: int, to_e164: str, attempt_no: int = 1
    ) -> CallAttempt:
        """Create a new call attempt record."""
        from datetime import UTC, datetime

        self.call_attempt_counter += 1
        call_attempt = CallAttempt(
            id=self.call_attempt_counter,
            alert_id=alert_id,
            to_e164=to_e164,
            attempt_no=attempt_no,
            started_at=datetime.now(UTC),
        )
        self.call_attempts[self.call_attempt_counter] = call_attempt
        return call_attempt

    async def update_call_attempt(self, call_attempt_id: int, **kwargs: Any) -> None:
        """Update call attempt record."""
        if call_attempt_id in self.call_attempts:
            for key, value in kwargs.items():
                setattr(self.call_attempts[call_attempt_id], key, value)
