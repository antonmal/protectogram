"""Panic notification Celery tasks for pre-scheduled guardian alerts."""

import logging

from app.celery_app import celery_app
from app.config.settings import get_settings
from app.database import get_sync_db_session
from app.models import PanicSession, PanicCycle, GuardianSessionStatus, Guardian
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# Import communication providers
from twilio.rest import Client
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Twilio client
twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

# Initialize Telegram bot
telegram_bot = Bot(token=settings.telegram_bot_token)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_guardian_telegram(
    self, session_id: str, guardian_id: str, cycle_number: int
):
    """Send Telegram notification to guardian."""

    try:
        with get_sync_db_session() as db:
            # Get session, guardian, and user data
            session = db.execute(
                select(PanicSession)
                .options(joinedload(PanicSession.user))
                .where(PanicSession.id == session_id)
            ).scalar_one_or_none()

            if not session or session.status != "active":
                logger.info(
                    f"Session {session_id} no longer active, skipping Telegram notification"
                )
                return f"Session {session_id} no longer active"

            guardian = db.execute(
                select(Guardian).where(Guardian.id == guardian_id)
            ).scalar_one_or_none()

            if not guardian or not guardian.telegram_chat_id:
                logger.warning(
                    f"Guardian {guardian_id} not found or no Telegram chat ID"
                )
                return f"Guardian {guardian_id} not found or no Telegram chat"

            user = session.user

            # Update guardian status
            guardian_status = db.execute(
                select(GuardianSessionStatus).where(
                    GuardianSessionStatus.session_id == session_id,
                    GuardianSessionStatus.guardian_id == guardian_id,
                )
            ).scalar_one_or_none()

            if guardian_status:
                guardian_status.telegram_sent = True
                guardian_status.status = "contact_attempted"
                db.commit()

            # Create message
            message = f"""
🚨 **EMERGENCY ALERT** 🚨

{user.first_name} has triggered a panic alert!

Message: {session.message or "Emergency assistance needed"}
Cycle: #{cycle_number}
Time: {session.created_at.strftime("%H:%M UTC")}

Please respond immediately:
• Tap ✅ if you can assist
• Tap ❌ if you cannot help right now
• Or press 1 during the phone call
"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ I can help",
                        callback_data=f"panic_ack_{session_id}_{guardian_id}",
                    ),
                    InlineKeyboardButton(
                        "❌ Cannot help",
                        callback_data=f"panic_decline_{session_id}_{guardian_id}",
                    ),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send message
            telegram_bot.send_message(
                chat_id=guardian.telegram_chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

            logger.info(
                f"Telegram notification sent to guardian {guardian_id} for session {session_id}"
            )
            return f"Telegram sent to guardian {guardian_id}"

    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        # Retry the task
        raise self.retry(countdown=self.default_retry_delay, exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_guardian_voice(self, session_id: str, guardian_id: str, cycle_number: int):
    """Make voice call to guardian."""

    try:
        with get_sync_db_session() as db:
            # Get session, guardian, and user data
            session = db.execute(
                select(PanicSession)
                .options(joinedload(PanicSession.user))
                .where(PanicSession.id == session_id)
            ).scalar_one_or_none()

            if not session or session.status != "active":
                logger.info(
                    f"Session {session_id} no longer active, skipping voice call"
                )
                return f"Session {session_id} no longer active"

            guardian = db.execute(
                select(Guardian).where(Guardian.id == guardian_id)
            ).scalar_one_or_none()

            if not guardian or not guardian.phone_number:
                logger.warning(f"Guardian {guardian_id} not found or no phone number")
                return f"Guardian {guardian_id} not found or no phone"

            # Update guardian status
            guardian_status = db.execute(
                select(GuardianSessionStatus).where(
                    GuardianSessionStatus.session_id == session_id,
                    GuardianSessionStatus.guardian_id == guardian_id,
                )
            ).scalar_one_or_none()

            if guardian_status:
                guardian_status.voice_call_made = True
                guardian_status.status = "contact_attempted"
                db.commit()

            # Create TwiML URL for voice call handling
            twiml_url = f"{settings.webhook_base_url}/webhooks/twilio/panic-call/{session_id}/{guardian_id}"

            # Make the call
            call = twilio_client.calls.create(
                to=guardian.phone_number,
                from_=settings.twilio_from_number,
                url=twiml_url,
                timeout=60,  # Ring for 60 seconds
            )

            logger.info(
                f"Voice call initiated for guardian {guardian_id} for session {session_id}: {call.sid}"
            )
            return f"Voice call made to guardian {guardian_id}: {call.sid}"

    except Exception as e:
        logger.error(f"Failed to make voice call: {e}")
        # Retry the task
        raise self.retry(countdown=self.default_retry_delay, exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def notify_guardian_sms(self, session_id: str, guardian_id: str, cycle_number: int):
    """Send SMS to guardian (30 seconds after voice call)."""

    try:
        with get_sync_db_session() as db:
            # Get session, guardian, and user data
            session = db.execute(
                select(PanicSession)
                .options(joinedload(PanicSession.user))
                .where(PanicSession.id == session_id)
            ).scalar_one_or_none()

            if not session or session.status != "active":
                logger.info(f"Session {session_id} no longer active, skipping SMS")
                return f"Session {session_id} no longer active"

            guardian = db.execute(
                select(Guardian).where(Guardian.id == guardian_id)
            ).scalar_one_or_none()

            if not guardian or not guardian.phone_number:
                logger.warning(f"Guardian {guardian_id} not found or no phone number")
                return f"Guardian {guardian_id} not found or no phone"

            user = session.user

            # Update guardian status
            guardian_status = db.execute(
                select(GuardianSessionStatus).where(
                    GuardianSessionStatus.session_id == session_id,
                    GuardianSessionStatus.guardian_id == guardian_id,
                )
            ).scalar_one_or_none()

            if guardian_status:
                guardian_status.sms_sent = True
                db.commit()

            # Create SMS text
            sms_text = f"""
🚨 EMERGENCY: {user.first_name} needs help!

Message: {session.message or "Emergency assistance needed"}
Cycle #{cycle_number}

Reply '1' if you can assist
Reply '0' if you cannot help

Session #{str(session.id)[:8]}
"""

            # Create SMS callback URL for response handling
            status_callback_url = f"{settings.webhook_base_url}/webhooks/twilio/panic-sms/{session_id}/{guardian_id}"

            # Send SMS
            message = twilio_client.messages.create(
                to=guardian.phone_number,
                from_=settings.twilio_from_number,
                body=sms_text.strip(),
                status_callback=status_callback_url,
            )

            logger.info(
                f"SMS sent to guardian {guardian_id} for session {session_id}: {message.sid}"
            )
            return f"SMS sent to guardian {guardian_id}: {message.sid}"

    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        # Retry the task
        raise self.retry(countdown=self.default_retry_delay, exc=e)


@celery_app.task(bind=True)
def check_cycle_completion(self, cycle_id: str):
    """Check if 10-minute cycle completed without acknowledgment."""

    try:
        with get_sync_db_session() as db:
            cycle = db.execute(
                select(PanicCycle)
                .options(joinedload(PanicCycle.session))
                .where(PanicCycle.id == cycle_id)
            ).scalar_one_or_none()

            if not cycle:
                logger.warning(f"Cycle {cycle_id} not found")
                return f"Cycle {cycle_id} not found"

            session = cycle.session

            if session.status != "active":
                logger.info(f"Session {session.id} no longer active")
                return f"Session {session.id} already resolved"

            # Mark cycle as expired
            cycle.status = "expired"
            db.commit()

            # Check if any guardian acknowledged during this cycle
            acknowledged_guardians = (
                db.execute(
                    select(GuardianSessionStatus).where(
                        GuardianSessionStatus.session_id == session.id,
                        GuardianSessionStatus.status == "acknowledged",
                    )
                )
                .scalars()
                .all()
            )

            if acknowledged_guardians:
                logger.info(f"Session {session.id} was acknowledged, no retry needed")
                return f"Session {session.id} already acknowledged"

            # No acknowledgments - offer retry to user
            notify_user_cycle_timeout.delay(str(session.id))

            logger.info(f"Cycle {cycle_id} expired, offering retry to user")
            return f"Cycle {cycle_id} completion check completed"

    except Exception as e:
        logger.error(f"Failed to check cycle completion: {e}")
        return f"Error checking cycle completion: {e}"


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def notify_user_cycle_timeout(self, session_id: str):
    """Offer user the option to start another 10-minute cycle."""

    try:
        with get_sync_db_session() as db:
            session = db.execute(
                select(PanicSession)
                .options(joinedload(PanicSession.user), joinedload(PanicSession.cycles))
                .where(PanicSession.id == session_id)
            ).scalar_one_or_none()

            if not session or session.status != "active":
                logger.info(f"Session {session_id} no longer active")
                return f"Session {session_id} no longer active"

            user = session.user
            cycle_count = len(session.cycles)

            retry_message = f"""
⏰ **10-Minute Alert Cycle Completed**

No guardian has acknowledged your emergency alert yet.

Session #{str(session.id)[:8]}
Cycle #{cycle_count} completed

Would you like to send another alert cycle to your guardians?
"""

            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔄 Send Another Alert",
                        callback_data=f"panic_retry_{session.id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🛑 Cancel Session", callback_data=f"panic_cancel_{session.id}"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send message to user
            telegram_bot.send_message(
                chat_id=user.telegram_user_id,
                text=retry_message,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )

            logger.info(f"Retry offer sent to user for session {session_id}")
            return f"Retry offer sent to user for session {session_id}"

    except Exception as e:
        logger.error(f"Failed to notify user of cycle timeout: {e}")
        raise self.retry(countdown=self.default_retry_delay, exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def notify_guardian_resolution(self, guardian_id: str, message: str, method: str):
    """Notify guardian that alert was resolved by someone else."""

    try:
        with get_sync_db_session() as db:
            guardian = db.execute(
                select(Guardian).where(Guardian.id == guardian_id)
            ).scalar_one_or_none()

            if not guardian:
                logger.warning(f"Guardian {guardian_id} not found")
                return f"Guardian {guardian_id} not found"

            if method == "telegram" and guardian.telegram_chat_id:
                telegram_bot.send_message(
                    chat_id=guardian.telegram_chat_id,
                    text=message,
                    parse_mode="Markdown",
                )
                logger.info(
                    f"Resolution notification sent to guardian {guardian_id} via Telegram"
                )

            elif method == "sms" and guardian.phone_number:
                twilio_client.messages.create(
                    to=guardian.phone_number,
                    from_=settings.twilio_from_number,
                    body=message,
                )
                logger.info(
                    f"Resolution notification sent to guardian {guardian_id} via SMS"
                )

            return (
                f"Resolution notification sent to guardian {guardian_id} via {method}"
            )

    except Exception as e:
        logger.error(f"Failed to send resolution notification: {e}")
        raise self.retry(countdown=self.default_retry_delay, exc=e)
