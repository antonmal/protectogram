"""Communication providers for panic alerts."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional

from app.config.settings import BaseAppSettings
from app.models import Guardian, PanicAlert

logger = logging.getLogger(__name__)


class NotificationMethod(str, Enum):
    """Available notification methods."""

    TELEGRAM = "telegram"
    VOICE_CALL = "voice_call"
    SMS = "sms"


class NotificationResult(str, Enum):
    """Notification attempt results."""

    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED_POSITIVE = "acknowledged_positive"
    ACKNOWLEDGED_NEGATIVE = "acknowledged_negative"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    TIMEOUT = "timeout"


class NotificationAttempt:
    """Result of a notification attempt."""

    def __init__(
        self,
        method: NotificationMethod,
        result: NotificationResult,
        provider_id: Optional[str] = None,
        error_message: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        responded_at: Optional[datetime] = None,
    ):
        self.method = method
        self.result = result
        self.provider_id = provider_id
        self.error_message = error_message
        self.sent_at = sent_at or datetime.utcnow()
        self.responded_at = responded_at


class CommunicationProvider(ABC):
    """Abstract base class for communication providers."""

    def __init__(self, settings: BaseAppSettings):
        self.settings = settings

    @abstractmethod
    async def send_telegram_message(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        """Send Telegram message to guardian."""
        pass

    @abstractmethod
    async def make_voice_call(
        self, guardian: Guardian, panic_alert: PanicAlert, caller_id: str
    ) -> NotificationAttempt:
        """Make voice call to guardian."""
        pass

    @abstractmethod
    async def send_sms(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        """Send SMS to guardian."""
        pass


class MockCommunicationProvider(CommunicationProvider):
    """Mock provider for testing."""

    async def send_telegram_message(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        logger.info(f"MOCK: Sending Telegram message to {guardian.name}: {message}")
        return NotificationAttempt(
            method=NotificationMethod.TELEGRAM,
            result=NotificationResult.DELIVERED,
            provider_id="mock_telegram_123",
        )

    async def make_voice_call(
        self, guardian: Guardian, panic_alert: PanicAlert, caller_id: str
    ) -> NotificationAttempt:
        logger.info(f"MOCK: Making voice call to {guardian.name} from {caller_id}")
        await asyncio.sleep(1)  # Simulate call duration
        return NotificationAttempt(
            method=NotificationMethod.VOICE_CALL,
            result=NotificationResult.NO_ANSWER,
            provider_id="mock_call_456",
        )

    async def send_sms(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        logger.info(f"MOCK: Sending SMS to {guardian.phone_number}: {message}")
        return NotificationAttempt(
            method=NotificationMethod.SMS,
            result=NotificationResult.DELIVERED,
            provider_id="mock_sms_789",
        )


class CommunicationService:
    """Service for managing communication providers and sending notifications."""

    def __init__(self, provider: CommunicationProvider):
        self.provider = provider

    async def notify_guardian(
        self,
        guardian: Guardian,
        panic_alert: PanicAlert,
        methods: List[NotificationMethod],
        caller_id: Optional[str] = None,
    ) -> List[NotificationAttempt]:
        """Send notifications to a guardian using specified methods."""
        attempts = []

        for method in methods:
            try:
                if method == NotificationMethod.TELEGRAM:
                    attempt = await self._send_telegram_notification(
                        guardian, panic_alert
                    )
                elif method == NotificationMethod.VOICE_CALL:
                    attempt = await self._make_voice_call(
                        guardian, panic_alert, caller_id
                    )
                elif method == NotificationMethod.SMS:
                    attempt = await self._send_sms_notification(guardian, panic_alert)
                else:
                    logger.warning(f"Unknown notification method: {method}")
                    continue

                attempts.append(attempt)

            except Exception as e:
                logger.error(
                    f"Failed to send {method} notification to {guardian.name}: {e}"
                )
                attempts.append(
                    NotificationAttempt(
                        method=method,
                        result=NotificationResult.FAILED,
                        error_message=str(e),
                    )
                )

        return attempts

    async def _send_telegram_notification(
        self, guardian: Guardian, panic_alert: PanicAlert
    ) -> NotificationAttempt:
        """Send Telegram notification to guardian."""
        # Check if guardian has telegram_chat_id
        if not hasattr(guardian, "telegram_chat_id") or not guardian.telegram_chat_id:
            logger.warning(
                f"Guardian {guardian.id} has no telegram_chat_id, skipping Telegram notification"
            )
            return NotificationAttempt(
                method=NotificationMethod.TELEGRAM,
                result=NotificationResult.FAILED,
                error_message="Guardian has not registered with Telegram bot",
            )

        message = self._format_telegram_message(panic_alert)
        return await self.provider.send_telegram_message(guardian, panic_alert, message)

    async def _make_voice_call(
        self,
        guardian: Guardian,
        panic_alert: PanicAlert,
        caller_id: Optional[str] = None,
    ) -> NotificationAttempt:
        """Make voice call to guardian."""
        if not caller_id:
            caller_id = panic_alert.user.phone_number
        return await self.provider.make_voice_call(guardian, panic_alert, caller_id)

    async def _send_sms_notification(
        self, guardian: Guardian, panic_alert: PanicAlert
    ) -> NotificationAttempt:
        """Send SMS notification to guardian."""
        message = self._format_sms_message(panic_alert)
        return await self.provider.send_sms(guardian, panic_alert, message)

    def _format_telegram_message(self, panic_alert: PanicAlert) -> str:
        """Format Telegram message for panic alert."""
        user = panic_alert.user
        message = "🚨 EMERGENCY ALERT 🚨\n\n"
        message += f"👤 {user.first_name}"
        if user.last_name:
            message += f" {user.last_name}"
        message += " needs immediate assistance!\n"
        message += f"📱 Contact: {user.phone_number}\n"

        if panic_alert.location:
            message += f"📍 Location: {panic_alert.location}\n"

        if panic_alert.message:
            message += f"💬 Message: {panic_alert.message}\n"

        message += (
            f"\n⏰ Alert triggered at: {panic_alert.created_at.strftime('%H:%M:%S')}\n"
        )
        message += "\n🔴 If this is an emergency, call emergency services immediately!"
        message += "\n✅ Reply with '1' to acknowledge or '9' if false alarm"

        return message

    def _format_sms_message(self, panic_alert: PanicAlert) -> str:
        """Format SMS message for panic alert."""
        user = panic_alert.user
        message = f"EMERGENCY: {user.first_name} needs help! "
        message += f"Contact {user.phone_number}. "

        if panic_alert.location:
            message += f"Location: {panic_alert.location}. "

        message += f"Time: {panic_alert.created_at.strftime('%H:%M')}. "
        message += "Reply 1=OK, 9=False alarm"

        return message


def get_communication_service(settings: BaseAppSettings) -> CommunicationService:
    """Factory function to get communication service."""

    if settings.environment == "development":
        # Use real Twilio for development testing
        from app.providers.twilio_provider import TwilioCommunicationProvider

        provider = TwilioCommunicationProvider(settings)
    else:
        # TODO: Initialize real providers based on settings
        from app.providers.twilio_provider import TwilioCommunicationProvider

        provider = TwilioCommunicationProvider(settings)

    return CommunicationService(provider)
