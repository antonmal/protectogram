"""Panic models for panic button events and sessions."""

import json
from typing import List
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel


class PanicAlert(BaseModel):
    """Main panic alert event tracking."""

    __tablename__ = "panic_alerts"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who triggered the panic alert",
    )

    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="Alert status: active, acknowledged, resolved",
    )

    location = Column(
        Text, nullable=True, comment="User's location when alert was triggered"
    )

    message = Column(Text, nullable=True, comment="Optional message from user")

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When alert was acknowledged by guardian",
    )

    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("guardians.id"),
        nullable=True,
        comment="Guardian who acknowledged the alert",
    )

    acknowledged_response = Column(
        String(10), nullable=True, comment="Guardian response: positive or negative"
    )

    cascade_timeout_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When cascade notifications should timeout",
    )

    retry_count = Column(
        Integer, default=0, nullable=False, comment="Number of manual retry attempts"
    )

    user = relationship("User", back_populates="panic_alerts")
    acknowledged_by_guardian = relationship("Guardian", foreign_keys=[acknowledged_by])
    notification_attempts = relationship(
        "PanicNotificationAttempt",
        back_populates="panic_alert",
        cascade="all, delete-orphan",
    )


class PanicNotificationAttempt(BaseModel):
    """Track individual notification attempts to guardians."""

    __tablename__ = "panic_notification_attempts"

    panic_alert_id = Column(
        UUID(as_uuid=True),
        ForeignKey("panic_alerts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to panic alert",
    )

    guardian_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Guardian receiving notification",
    )

    method = Column(
        String(20),
        nullable=False,
        comment="Notification method: telegram, voice_call, sms",
    )

    provider_id = Column(
        String(100),
        nullable=True,
        comment="Provider-specific ID (Twilio SID, Telegram message ID)",
    )

    status = Column(
        String(30),
        nullable=False,
        comment="Attempt status: sent, delivered, failed, acknowledged_positive, acknowledged_negative",
    )

    response = Column(
        String(10),
        nullable=True,
        comment="DTMF response from guardian: 1 (positive), 9 (negative)",
    )

    error_message = Column(
        Text, nullable=True, comment="Error details if attempt failed"
    )

    sent_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When notification was sent",
    )

    responded_at = Column(
        DateTime(timezone=True), nullable=True, comment="When guardian responded"
    )

    panic_alert = relationship("PanicAlert", back_populates="notification_attempts")
    guardian = relationship("Guardian")


class PanicSession(BaseModel):
    """Panic session - can have multiple 10-minute cycles."""

    __tablename__ = "panic_sessions"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who triggered the panic session",
    )

    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="Session status: active, acknowledged, cancelled, expired",
    )

    message = Column(Text, nullable=True, comment="Optional message from user")

    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When session was acknowledged by first guardian",
    )

    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey("guardians.id"),
        nullable=True,
        comment="First guardian who acknowledged the session",
    )

    cancelled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When session was cancelled by user",
    )

    # Relationships
    user = relationship("User")
    acknowledged_by_guardian = relationship("Guardian", foreign_keys=[acknowledged_by])
    cycles = relationship(
        "PanicCycle", back_populates="session", cascade="all, delete-orphan"
    )
    guardian_statuses = relationship(
        "GuardianSessionStatus", back_populates="session", cascade="all, delete-orphan"
    )


class PanicCycle(BaseModel):
    """Individual 10-minute notification cycle within a session."""

    __tablename__ = "panic_cycles"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("panic_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to panic session",
    )

    cycle_number = Column(
        Integer,
        nullable=False,
        comment="Cycle number within session (1, 2, 3...)",
    )

    status = Column(
        String(20),
        nullable=False,
        default="active",
        comment="Cycle status: active, completed, expired",
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this cycle expires (10 minutes from start)",
    )

    scheduled_task_ids = Column(
        Text,
        nullable=True,
        comment="JSON array of Celery task IDs for cancellation",
    )

    # Relationships
    session = relationship("PanicSession", back_populates="cycles")

    def get_task_ids(self) -> List[str]:
        """Get scheduled task IDs as a list."""
        if self.scheduled_task_ids:
            return json.loads(self.scheduled_task_ids)
        return []

    def set_task_ids(self, task_ids: List[str]):
        """Set scheduled task IDs from a list."""
        self.scheduled_task_ids = json.dumps(task_ids)


class GuardianSessionStatus(BaseModel):
    """Track each guardian's status throughout the entire panic session."""

    __tablename__ = "guardian_session_statuses"

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("panic_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to panic session",
    )

    guardian_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Guardian being tracked",
    )

    status = Column(
        String(30),
        nullable=False,
        default="scheduled",
        comment="Overall status: scheduled, contact_attempted, acknowledged, declined, no_response",
    )

    # Detailed tracking
    telegram_sent = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether Telegram notification was sent",
    )

    voice_call_made = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether voice call was made",
    )

    sms_sent = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether SMS was sent",
    )

    # Response tracking
    responded_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When guardian first responded",
    )

    response_type = Column(
        String(10),
        nullable=True,
        comment="Guardian response: positive or negative",
    )

    response_method = Column(
        String(20),
        nullable=True,
        comment="How guardian responded: telegram, voice, sms",
    )

    # Exclusion tracking
    excluded_from_cycle = Column(
        Integer,
        nullable=True,
        comment="Which cycle number they were excluded from (if declined)",
    )

    # Relationships
    session = relationship("PanicSession", back_populates="guardian_statuses")
    guardian = relationship("Guardian")
