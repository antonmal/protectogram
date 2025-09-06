"""Panic model for panic button events."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
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
