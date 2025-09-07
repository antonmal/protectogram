"""Enhanced panic session service with Celery task management."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from celery import current_app
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    PanicSession,
    PanicCycle,
    GuardianSessionStatus,
    Guardian,
    User,
    UserGuardian,
)
from app.tasks.panic_notifications import (
    notify_guardian_telegram,
    notify_guardian_voice,
    notify_guardian_sms,
    check_cycle_completion,
    notify_guardian_resolution,
)

logger = logging.getLogger(__name__)


class PanicSessionService:
    """Service for managing panic sessions with Celery task scheduling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_panic_session(
        self, user_id: UUID, message: Optional[str] = None
    ) -> PanicSession:
        """Start new panic session with immediate task scheduling."""

        # Check for existing active session
        existing_session = await self._get_active_session(user_id)
        if existing_session:
            logger.warning(
                f"User {user_id} already has active panic session: {existing_session.id}"
            )
            return existing_session

        # Create new panic session
        session = PanicSession(user_id=user_id, message=message, status="active")

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"Created panic session {session.id} for user {user_id}")

        # Initialize guardian statuses
        await self._initialize_guardian_statuses(session.id, user_id)

        # Send immediate user confirmation
        await self._send_user_confirmation(session)

        # Start first 10-minute cycle
        await self.start_new_cycle(session.id)

        return session

    async def start_new_cycle(self, session_id: UUID) -> PanicCycle:
        """Start a new 10-minute notification cycle."""

        session = await self._get_session_with_relations(session_id)
        if not session or session.status != "active":
            raise ValueError(f"Cannot start cycle for inactive session {session_id}")

        # Get cycle number
        existing_cycles = len(session.cycles)
        cycle_number = existing_cycles + 1

        # Create cycle
        cycle = PanicCycle(
            session_id=session_id,
            cycle_number=cycle_number,
            status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        self.db.add(cycle)
        await self.db.commit()
        await self.db.refresh(cycle)

        logger.info(
            f"Created cycle {cycle.id} (#{cycle_number}) for session {session_id}"
        )

        # Schedule ALL tasks for this 10-minute cycle at once
        task_ids = await self._schedule_complete_cycle(cycle)

        # Store task IDs for cancellation
        cycle.set_task_ids(task_ids)
        await self.db.commit()

        logger.info(f"Scheduled {len(task_ids)} tasks for cycle {cycle.id}")

        return cycle

    async def _schedule_complete_cycle(self, cycle: PanicCycle) -> List[str]:
        """Pre-schedule ALL notification tasks for the entire 10-minute cycle."""

        session = await self._get_session_with_relations(cycle.session_id)
        guardians = await self._get_available_guardians(session)

        if not guardians:
            logger.warning(f"No available guardians for session {session.id}")
            return []

        task_ids = []

        # Schedule guardian notifications in 60-second intervals
        for i, guardian in enumerate(guardians):
            delay_seconds = i * 60  # 0s, 60s, 120s, 180s...

            # If we exceed 10 minutes, cycle back to first guardian
            if delay_seconds >= 600:  # 10 minutes
                # Start next round, but don't exceed 10 minutes total
                round_delay = delay_seconds - 600
                if round_delay < 600:  # Still within 10-minute window
                    delay_seconds = 600 - round_delay
                else:
                    break  # Beyond 10-minute window

            # Schedule Telegram notification (immediate)
            telegram_task = notify_guardian_telegram.apply_async(
                args=[str(cycle.session_id), str(guardian.id), cycle.cycle_number],
                countdown=delay_seconds,
                task_id=f"telegram_{cycle.id}_{guardian.id}_{delay_seconds}",
            )
            task_ids.append(telegram_task.id)

            # Schedule voice call (same time as Telegram)
            voice_task = notify_guardian_voice.apply_async(
                args=[str(cycle.session_id), str(guardian.id), cycle.cycle_number],
                countdown=delay_seconds,
                task_id=f"voice_{cycle.id}_{guardian.id}_{delay_seconds}",
            )
            task_ids.append(voice_task.id)

            # Schedule SMS (30 seconds after voice)
            if delay_seconds + 30 < 600:  # Still within 10-minute window
                sms_task = notify_guardian_sms.apply_async(
                    args=[str(cycle.session_id), str(guardian.id), cycle.cycle_number],
                    countdown=delay_seconds + 30,
                    task_id=f"sms_{cycle.id}_{guardian.id}_{delay_seconds + 30}",
                )
                task_ids.append(sms_task.id)

        # Schedule cycle completion check at 10 minutes
        completion_task = check_cycle_completion.apply_async(
            args=[str(cycle.id)],
            countdown=600,  # 10 minutes
            task_id=f"completion_{cycle.id}",
        )
        task_ids.append(completion_task.id)

        logger.info(f"Pre-scheduled {len(task_ids)} tasks for cycle {cycle.id}")
        return task_ids

    async def handle_guardian_response(
        self,
        session_id: UUID,
        guardian_id: UUID,
        response_type: str,  # "positive", "negative"
        response_method: str,  # "telegram", "voice", "sms"
    ) -> dict:
        """Handle guardian response - allow multiple acknowledgments."""

        session = await self._get_session_with_relations(session_id)
        if not session:
            return {"status": "session_not_found"}

        if session.status != "active":
            return {"status": "session_not_active"}

        # Update guardian status
        guardian_status = await self._get_guardian_status(session_id, guardian_id)
        if not guardian_status:
            logger.warning(
                f"Guardian status not found for session {session_id}, guardian {guardian_id}"
            )
            return {"status": "guardian_status_not_found"}

        guardian_status.responded_at = datetime.now(timezone.utc)
        guardian_status.response_type = response_type
        guardian_status.response_method = response_method

        if response_type == "positive":
            # Positive acknowledgment
            guardian_status.status = "acknowledged"

            # Update session if not already acknowledged
            if session.status == "active":
                session.status = "acknowledged"
                session.acknowledged_at = datetime.now(timezone.utc)
                session.acknowledged_by = guardian_id

                logger.info(
                    f"Session {session_id} acknowledged by guardian {guardian_id}"
                )
            else:
                # Session already acknowledged by someone else
                logger.info(
                    f"Additional acknowledgment from guardian {guardian_id} for session {session_id}"
                )

            await self.db.commit()

            # Cancel ALL scheduled tasks for this session
            await self._cancel_all_session_tasks(session_id)

            # Notify user of acknowledgment
            await self._notify_user_acknowledgment(session, guardian_id)

            # Notify all OTHER guardians that someone acknowledged
            await self._notify_guardians_acknowledgment(session, guardian_id)

            return {"status": "acknowledged", "acknowledged_by": guardian_id}

        elif response_type == "negative":
            # Negative response - exclude from further notifications
            guardian_status.status = "declined"
            current_cycle = await self._get_current_cycle(session_id)
            if current_cycle:
                guardian_status.excluded_from_cycle = current_cycle.cycle_number

            await self.db.commit()

            logger.info(f"Guardian {guardian_id} declined session {session_id}")
            return {"status": "declined", "guardian_excluded": guardian_id}

        return {"status": "unknown_response_type"}

    async def cancel_session(self, session_id: UUID, user_id: UUID) -> bool:
        """Cancel panic session (user-only operation)."""

        session = await self._get_session_with_relations(session_id)
        if not session:
            return False

        if session.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to cancel session {session_id} they don't own"
            )
            return False

        if session.status != "active":
            logger.warning(f"Session {session_id} is not active, cannot cancel")
            return False

        # Update session
        session.status = "cancelled"
        session.cancelled_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Cancel all scheduled tasks
        await self._cancel_all_session_tasks(session_id)

        logger.info(f"Session {session_id} cancelled by user {user_id}")
        return True

    async def _cancel_all_session_tasks(self, session_id: UUID):
        """Cancel all scheduled Celery tasks for this session."""

        session = await self._get_session_with_relations(session_id)
        if not session:
            return

        cancelled_count = 0
        for cycle in session.cycles:
            if cycle.scheduled_task_ids:
                task_ids = cycle.get_task_ids()
                for task_id in task_ids:
                    try:
                        current_app.control.revoke(task_id, terminate=True)
                        cancelled_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to revoke task {task_id}: {e}")

        logger.info(f"Cancelled {cancelled_count} tasks for session {session_id}")

    async def _notify_user_acknowledgment(
        self, session: PanicSession, guardian_id: UUID
    ):
        """Notify user that a guardian acknowledged the alert."""

        guardian = await self._get_guardian(guardian_id)
        if not guardian:
            return

        # Import here to avoid circular import

        # Bot integration will be handled by telegram client

        # This will be handled by the Telegram client integration
        # For now, we'll use the task system
        message = f"""
✅ **ALERT ACKNOWLEDGED** ✅

Your emergency alert has been acknowledged!

Guardian: {guardian.name}
Time: {session.acknowledged_at.strftime("%H:%M UTC")}
Session: #{str(session.id)[:8]}

{guardian.name} is aware of your situation and will assist you.
"""

        # Use Celery task to send notification
        notify_guardian_resolution.delay(str(session.user_id), message, "telegram")

    async def _notify_guardians_acknowledgment(
        self, session: PanicSession, acknowledging_guardian_id: UUID
    ):
        """Notify all guardians that someone acknowledged the alert."""

        acknowledging_guardian = await self._get_guardian(acknowledging_guardian_id)
        user = await self._get_user(session.user_id)

        if not acknowledging_guardian or not user:
            return

        notification_text = f"""
✅ **ALERT RESOLVED** ✅

The emergency alert for {user.first_name} has been acknowledged by {acknowledging_guardian.name}.

No further action is needed from you at this time.

Session #{str(session.id)[:8]} - Resolved at {session.acknowledged_at.strftime("%H:%M UTC")}
"""

        # Send to all guardians except the one who acknowledged
        for guardian_status in session.guardian_statuses:
            if guardian_status.guardian_id != acknowledging_guardian_id:
                guardian = await self._get_guardian(guardian_status.guardian_id)
                if guardian:
                    # Telegram notification
                    notify_guardian_resolution.delay(
                        str(guardian.id), notification_text, "telegram"
                    )

                    # SMS notification
                    sms_text = f"ALERT RESOLVED: Emergency for {user.first_name} acknowledged by {acknowledging_guardian.name}. Session #{str(session.id)[:8]}"
                    notify_guardian_resolution.delay(str(guardian.id), sms_text, "sms")

    async def _send_user_confirmation(self, session: PanicSession):
        """Send immediate confirmation to user."""

        user = await self._get_user(session.user_id)
        if not user:
            return

        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        from app.config.settings import get_settings

        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)

        confirmation_text = f"""
🚨 **PANIC ALERT ACTIVATED** 🚨

Your emergency alert has been sent to your guardians.

Alert ID: #{str(session.id)[:8]}
Time: {session.created_at.strftime("%H:%M UTC")}
Message: {session.message or "Emergency assistance needed"}

Status: 📞 Contacting guardians...
"""

        keyboard = [
            [
                InlineKeyboardButton(
                    "🛑 Cancel Alert", callback_data=f"panic_cancel_{session.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Alert Status", callback_data=f"panic_status_{session.id}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            bot.send_message(
                chat_id=user.telegram_user_id,
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send user confirmation: {e}")

    async def _initialize_guardian_statuses(self, session_id: UUID, user_id: UUID):
        """Initialize guardian statuses for the session."""

        guardians = await self._get_user_guardians(user_id)

        for guardian in guardians:
            status = GuardianSessionStatus(
                session_id=session_id, guardian_id=guardian.id, status="scheduled"
            )
            self.db.add(status)

        await self.db.commit()
        logger.info(
            f"Initialized {len(guardians)} guardian statuses for session {session_id}"
        )

    async def _get_active_session(self, user_id: UUID) -> Optional[PanicSession]:
        """Get active panic session for a user."""

        result = await self.db.execute(
            select(PanicSession).where(
                PanicSession.user_id == user_id, PanicSession.status == "active"
            )
        )
        return result.scalar_one_or_none()

    async def _get_session_with_relations(
        self, session_id: UUID
    ) -> Optional[PanicSession]:
        """Get panic session with all relationships loaded."""

        result = await self.db.execute(
            select(PanicSession)
            .options(
                selectinload(PanicSession.user),
                selectinload(PanicSession.cycles),
                selectinload(PanicSession.guardian_statuses),
                selectinload(PanicSession.acknowledged_by_guardian),
            )
            .where(PanicSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _get_current_cycle(self, session_id: UUID) -> Optional[PanicCycle]:
        """Get current active cycle for a session."""

        result = await self.db.execute(
            select(PanicCycle)
            .where(PanicCycle.session_id == session_id, PanicCycle.status == "active")
            .order_by(PanicCycle.cycle_number.desc())
        )
        return result.scalar_one_or_none()

    async def _get_guardian_status(
        self, session_id: UUID, guardian_id: UUID
    ) -> Optional[GuardianSessionStatus]:
        """Get guardian status for a session."""

        result = await self.db.execute(
            select(GuardianSessionStatus).where(
                GuardianSessionStatus.session_id == session_id,
                GuardianSessionStatus.guardian_id == guardian_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_available_guardians(self, session: PanicSession) -> List[Guardian]:
        """Get guardians available for notification (not declined in current cycle)."""

        current_cycle = await self._get_current_cycle(session.id)
        current_cycle_number = current_cycle.cycle_number if current_cycle else 1

        # Get all guardians for user
        guardians = await self._get_user_guardians(session.user_id)

        # Filter out declined guardians for current cycle
        available_guardians = []
        for guardian in guardians:
            status = await self._get_guardian_status(session.id, guardian.id)
            if (
                not status
                or status.status != "declined"
                or (
                    status.excluded_from_cycle
                    and status.excluded_from_cycle < current_cycle_number
                )
            ):
                available_guardians.append(guardian)

        return available_guardians

    async def _get_user_guardians(self, user_id: UUID) -> List[Guardian]:
        """Get all guardians for a user ordered by priority."""

        result = await self.db.execute(
            select(Guardian)
            .join(UserGuardian)
            .where(UserGuardian.user_id == user_id)
            .order_by(UserGuardian.priority_order.asc())
        )
        return list(result.scalars().all())

    async def _get_guardian(self, guardian_id: UUID) -> Optional[Guardian]:
        """Get guardian by ID."""

        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        return result.scalar_one_or_none()

    async def _get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""

        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
