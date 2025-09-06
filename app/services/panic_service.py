"""Service for handling panic alerts and cascading notifications."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.communications import (
    CommunicationService,
    NotificationMethod,
    NotificationResult,
    get_communication_service,
)
from app.config.settings import get_settings
from app.models import Guardian, PanicAlert, PanicNotificationAttempt, UserGuardian

logger = logging.getLogger(__name__)


class PanicAlertService:
    """Service for managing panic alerts and notifications."""

    def __init__(
        self,
        db: AsyncSession,
        communication_service: Optional[CommunicationService] = None,
    ):
        self.db = db
        self.communication_service = communication_service or get_communication_service(
            get_settings()
        )

    async def trigger_panic_alert(
        self,
        user_id: UUID,
        location: Optional[str] = None,
        message: Optional[str] = None,
    ) -> PanicAlert:
        """Trigger a new panic alert for a user."""

        # Check for active alerts
        existing_alert = await self._get_active_alert(user_id)
        if existing_alert:
            logger.warning(
                f"User {user_id} already has an active panic alert: {existing_alert.id}"
            )
            return existing_alert

        # Create new panic alert
        panic_alert = PanicAlert(
            user_id=user_id,
            location=location,
            message=message,
            cascade_timeout_at=datetime.now(timezone.utc)
            + timedelta(minutes=15),  # 15-minute timeout
        )

        self.db.add(panic_alert)
        await self.db.commit()
        await self.db.refresh(panic_alert)

        logger.info(f"Created panic alert {panic_alert.id} for user {user_id}")

        # Start cascade notification process
        asyncio.create_task(self._start_cascade_notifications(panic_alert.id))

        return panic_alert

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        guardian_id: UUID,
        response: str,  # "positive" or "negative"
    ) -> bool:
        """Acknowledge a panic alert from a guardian."""

        panic_alert = await self._get_alert_with_user(alert_id)
        if not panic_alert:
            logger.error(f"Panic alert {alert_id} not found")
            return False

        if panic_alert.status != "active":
            logger.warning(
                f"Panic alert {alert_id} is not active, status: {panic_alert.status}"
            )
            return False

        # Update alert status
        panic_alert.acknowledged_at = datetime.now(timezone.utc)
        panic_alert.acknowledged_by = guardian_id
        panic_alert.acknowledged_response = response
        panic_alert.status = "acknowledged"

        # Update notification attempt that was acknowledged
        attempt = await self._get_latest_attempt(alert_id, guardian_id)
        if attempt:
            attempt.responded_at = datetime.now(timezone.utc)
            attempt.response = "1" if response == "positive" else "9"
            attempt.status = (
                NotificationResult.ACKNOWLEDGED_POSITIVE.value
                if response == "positive"
                else NotificationResult.ACKNOWLEDGED_NEGATIVE.value
            )

        await self.db.commit()

        logger.info(
            f"Panic alert {alert_id} acknowledged by guardian {guardian_id} with response: {response}"
        )

        # Stop any pending notifications
        asyncio.create_task(self._stop_cascade_notifications(alert_id))

        return True

    async def retry_alert(self, alert_id: UUID) -> bool:
        """Manually retry a panic alert."""

        panic_alert = await self._get_alert_with_user(alert_id)
        if not panic_alert:
            return False

        if panic_alert.status == "acknowledged":
            logger.warning(f"Cannot retry acknowledged alert {alert_id}")
            return False

        # Increment retry count and extend timeout
        panic_alert.retry_count += 1
        panic_alert.cascade_timeout_at = datetime.now(timezone.utc) + timedelta(
            minutes=15
        )
        panic_alert.status = "active"

        await self.db.commit()

        logger.info(
            f"Retrying panic alert {alert_id}, attempt #{panic_alert.retry_count}"
        )

        # Restart cascade notifications
        asyncio.create_task(self._start_cascade_notifications(alert_id))

        return True

    async def resolve_alert(self, alert_id: UUID) -> bool:
        """Manually resolve a panic alert."""

        panic_alert = await self._get_alert_with_user(alert_id)
        if not panic_alert:
            return False

        panic_alert.status = "resolved"
        await self.db.commit()

        logger.info(f"Panic alert {alert_id} manually resolved")

        # Stop any pending notifications
        asyncio.create_task(self._stop_cascade_notifications(alert_id))

        return True

    async def get_user_alerts(
        self, user_id: UUID, status: Optional[str] = None, limit: int = 50
    ) -> List[PanicAlert]:
        """Get panic alerts for a user."""

        query = select(PanicAlert).where(PanicAlert.user_id == user_id)

        if status:
            query = query.where(PanicAlert.status == status)

        query = query.order_by(PanicAlert.created_at.desc()).limit(limit)
        query = query.options(selectinload(PanicAlert.notification_attempts))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _start_cascade_notifications(self, alert_id: UUID):
        """Start the cascade notification process for an alert."""

        while True:
            panic_alert = await self._get_alert_with_user(alert_id)
            if not panic_alert:
                logger.error(f"Alert {alert_id} not found, stopping cascade")
                break

            if panic_alert.status != "active":
                logger.info(
                    f"Alert {alert_id} no longer active ({panic_alert.status}), stopping cascade"
                )
                break

            if datetime.now(timezone.utc) > panic_alert.cascade_timeout_at:
                logger.info(f"Alert {alert_id} timed out, stopping cascade")
                panic_alert.status = "timeout"
                await self.db.commit()
                break

            # Get guardians for this user
            guardians = await self._get_user_guardians(panic_alert.user_id)
            if not guardians:
                logger.warning(f"No guardians found for user {panic_alert.user_id}")
                # For testing: stop cascade if no guardians (don't wait indefinitely)
                panic_alert.status = "no_guardians"
                await self.db.commit()
                break

            # Notify all guardians in parallel
            notification_tasks = []
            for guardian in guardians:
                task = self._notify_guardian_with_cascade(alert_id, guardian)
                notification_tasks.append(task)

            if notification_tasks:
                await asyncio.gather(*notification_tasks, return_exceptions=True)

            # Check if alert was acknowledged during notifications
            await self.db.refresh(panic_alert)
            if panic_alert.status != "active":
                break

            # Wait 60 seconds before next round
            await asyncio.sleep(60)

    async def _notify_guardian_with_cascade(self, alert_id: UUID, guardian: Guardian):
        """Notify a single guardian with cascade logic."""

        panic_alert = await self._get_alert_with_user(alert_id)
        if not panic_alert or panic_alert.status != "active":
            return

        try:
            # Step 1: Make voice call (skip Telegram for now)
            call_task = self.communication_service.notify_guardian(
                guardian,
                panic_alert,
                [NotificationMethod.VOICE_CALL],
                caller_id=panic_alert.user.phone_number,
            )

            call_attempts = await call_task

            # Save notification attempts
            all_attempts = []
            if isinstance(call_attempts, list):
                all_attempts.extend(call_attempts)

            await self._save_notification_attempts(alert_id, guardian.id, all_attempts)

            # Step 2: Wait 30 seconds, then send SMS if no acknowledgment
            await asyncio.sleep(30)

            # Refresh alert to check if acknowledged
            await self.db.refresh(panic_alert)
            if panic_alert.status != "active":
                return

            # Send SMS backup
            sms_attempts = await self.communication_service.notify_guardian(
                guardian, panic_alert, [NotificationMethod.SMS]
            )

            await self._save_notification_attempts(alert_id, guardian.id, sms_attempts)

        except Exception as e:
            logger.error(
                f"Error notifying guardian {guardian.id} for alert {alert_id}: {e}"
            )

            # Save failed attempt
            failed_attempt = PanicNotificationAttempt(
                panic_alert_id=alert_id,
                guardian_id=guardian.id,
                method="cascade_error",
                status=NotificationResult.FAILED.value,
                error_message=str(e),
            )
            self.db.add(failed_attempt)
            await self.db.commit()

    async def _save_notification_attempts(
        self, alert_id: UUID, guardian_id: UUID, attempts: list
    ):
        """Save notification attempts to database."""

        for attempt in attempts:
            db_attempt = PanicNotificationAttempt(
                panic_alert_id=alert_id,
                guardian_id=guardian_id,
                method=attempt.method.value,
                provider_id=attempt.provider_id,
                status=attempt.result.value,
                error_message=attempt.error_message,
                sent_at=attempt.sent_at,
                responded_at=attempt.responded_at,
                response=getattr(attempt, "response", None),
            )
            self.db.add(db_attempt)

        await self.db.commit()

    async def _stop_cascade_notifications(self, alert_id: UUID):
        """Stop cascade notifications for an alert."""
        # Note: In production, you might want to use a task queue like Celery
        # to properly manage and cancel background tasks
        logger.info(f"Stopping cascade notifications for alert {alert_id}")

    async def _get_active_alert(self, user_id: UUID) -> Optional[PanicAlert]:
        """Get active panic alert for a user."""

        query = select(PanicAlert).where(
            PanicAlert.user_id == user_id, PanicAlert.status == "active"
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_alert_with_user(self, alert_id: UUID) -> Optional[PanicAlert]:
        """Get panic alert with user information."""

        query = select(PanicAlert).where(PanicAlert.id == alert_id)
        query = query.options(selectinload(PanicAlert.user))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_guardians(self, user_id: UUID) -> List[Guardian]:
        """Get all guardians for a user."""

        query = (
            select(Guardian).join(UserGuardian).where(UserGuardian.user_id == user_id)
        )
        query = query.order_by(UserGuardian.priority_order.asc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_latest_attempt(
        self, alert_id: UUID, guardian_id: UUID
    ) -> Optional[PanicNotificationAttempt]:
        """Get the latest notification attempt for a guardian."""

        query = (
            select(PanicNotificationAttempt)
            .where(
                PanicNotificationAttempt.panic_alert_id == alert_id,
                PanicNotificationAttempt.guardian_id == guardian_id,
            )
            .order_by(PanicNotificationAttempt.sent_at.desc())
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()
