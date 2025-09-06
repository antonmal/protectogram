"""Twilio communication provider for real SMS and voice calls."""

import logging
from datetime import datetime

from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from app.config.settings import BaseAppSettings
from app.core.communications import (
    CommunicationProvider,
    NotificationAttempt,
    NotificationMethod,
    NotificationResult,
)
from app.models import Guardian, PanicAlert

logger = logging.getLogger(__name__)


class TwilioCommunicationProvider(CommunicationProvider):
    """Real Twilio provider for SMS and voice calls."""

    def __init__(self, settings: BaseAppSettings):
        super().__init__(settings)
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = settings.twilio_from_number

    async def send_telegram_message(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        """Send Telegram message (not implemented in Twilio provider)."""
        logger.warning("Telegram messaging not supported by Twilio provider")
        return NotificationAttempt(
            method=NotificationMethod.TELEGRAM,
            result=NotificationResult.FAILED,
            error_message="Telegram not supported by Twilio provider",
        )

    async def make_voice_call(
        self, guardian: Guardian, panic_alert: PanicAlert, caller_id: str
    ) -> NotificationAttempt:
        """Make real voice call to guardian."""

        try:
            # Create TwiML for the call
            twiml_url = f"{self.settings.webhook_base_url}/webhooks/twilio/voice"

            logger.info(
                f"Making voice call to {guardian.phone_number} from {caller_id}"
            )

            call = self.client.calls.create(
                to=guardian.phone_number,
                from_=self.from_number,
                url=twiml_url,
                method="POST",
                timeout=30,  # 30 seconds timeout
                # Use the panic user's phone as caller ID if available
                # caller_id=caller_id  # Note: Caller ID may require verification
            )

            logger.info(f"Voice call initiated: SID={call.sid}")

            return NotificationAttempt(
                method=NotificationMethod.VOICE_CALL,
                result=NotificationResult.SENT,
                provider_id=call.sid,
                sent_at=datetime.utcnow(),
            )

        except TwilioException as e:
            logger.error(f"Twilio voice call failed: {e}")
            return NotificationAttempt(
                method=NotificationMethod.VOICE_CALL,
                result=NotificationResult.FAILED,
                error_message=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error making voice call: {e}")
            return NotificationAttempt(
                method=NotificationMethod.VOICE_CALL,
                result=NotificationResult.FAILED,
                error_message=str(e),
            )

    async def send_sms(
        self, guardian: Guardian, panic_alert: PanicAlert, message: str
    ) -> NotificationAttempt:
        """Send real SMS to guardian."""

        try:
            logger.info(f"Sending SMS to {guardian.phone_number}: {message[:50]}...")

            sms = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=guardian.phone_number,
                # Set webhook for delivery status
                status_callback=f"{self.settings.webhook_base_url}/webhooks/twilio/sms",
            )

            logger.info(f"SMS sent: SID={sms.sid}")

            return NotificationAttempt(
                method=NotificationMethod.SMS,
                result=NotificationResult.SENT,
                provider_id=sms.sid,
                sent_at=datetime.utcnow(),
            )

        except TwilioException as e:
            logger.error(f"Twilio SMS failed: {e}")
            return NotificationAttempt(
                method=NotificationMethod.SMS,
                result=NotificationResult.FAILED,
                error_message=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return NotificationAttempt(
                method=NotificationMethod.SMS,
                result=NotificationResult.FAILED,
                error_message=str(e),
            )
