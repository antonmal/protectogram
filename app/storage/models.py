"""SQLAlchemy models for Protectogram database."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model representing Telegram users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    phone_e164 = Column(String(20), nullable=True)
    display_name = Column(String(100), nullable=False)
    preferred_locale = Column(String(10), default="ru-RU", nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    member_links_as_watcher = relationship(
        "MemberLink", foreign_keys="MemberLink.watcher_user_id"
    )
    member_links_as_traveler = relationship(
        "MemberLink", foreign_keys="MemberLink.traveler_user_id"
    )
    incidents = relationship("Incident", foreign_keys="Incident.traveler_user_id")
    acknowledged_incidents = relationship(
        "Incident", foreign_keys="Incident.acknowledged_by_user_id"
    )


class MemberLink(Base):
    """Link between watcher and traveler users."""

    __tablename__ = "member_links"

    id = Column(Integer, primary_key=True)
    watcher_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    traveler_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, inactive
    call_priority = Column(Integer, default=1, nullable=False)
    ring_timeout_sec = Column(Integer, default=25, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    retry_backoff_sec = Column(Integer, default=60, nullable=False)
    telegram_enabled = Column(Boolean, default=True, nullable=False)
    calls_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    watcher = relationship(
        "User", foreign_keys=[watcher_user_id], overlaps="member_links_as_watcher"
    )
    traveler = relationship(
        "User", foreign_keys=[traveler_user_id], overlaps="member_links_as_traveler"
    )

    # Indexes
    __table_args__ = (
        Index(
            "idx_member_links_traveler_priority", "traveler_user_id", "call_priority"
        ),
    )


class Incident(Base):
    """Panic incident model."""

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    traveler_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(20), default="active", nullable=False
    )  # active, acknowledged, canceled, exhausted
    acknowledged_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ack_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    exhausted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    traveler = relationship(
        "User", foreign_keys=[traveler_user_id], overlaps="incidents"
    )
    acknowledged_by = relationship(
        "User",
        foreign_keys=[acknowledged_by_user_id],
        overlaps="acknowledged_incidents",
    )
    alerts = relationship("Alert", back_populates="incident")
    scheduled_actions = relationship("ScheduledAction", back_populates="incident")

    # Constraints will be handled in migration
    __table_args__ = ()


class Alert(Base):
    """Alert model for notifications sent to watchers."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    type = Column(String(20), nullable=False)  # telegram, call
    audience_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, sent, failed
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    incident = relationship("Incident", back_populates="alerts")
    audience_user = relationship("User", foreign_keys=[audience_user_id])
    call_attempts = relationship("CallAttempt", back_populates="alert")


class CallAttempt(Base):
    """Individual call attempt model."""

    __tablename__ = "call_attempts"

    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    to_e164 = Column(String(20), nullable=False)
    telnyx_call_id = Column(String(100), nullable=True)
    attempt_no = Column(Integer, default=1, nullable=False)
    result = Column(String(20), nullable=True)  # answered, busy, no_answer, failed
    dtmf_received = Column(String(10), nullable=True)
    amd_result = Column(String(50), nullable=True)  # human, machine, unknown
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="call_attempts")

    # Indexes
    __table_args__ = (
        Index("idx_call_attempts_alert_attempt", "alert_id", "attempt_no"),
    )


class InboxEvent(Base):
    """Inbox events for idempotency."""

    __tablename__ = "inbox_events"

    id = Column(Integer, primary_key=True)
    provider = Column(String(20), nullable=False)  # telegram, telnyx
    provider_event_id = Column(String(100), nullable=False)
    received_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    payload_json = Column(Text, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Unique constraint for idempotency
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_inbox_provider_event"
        ),
        Index("idx_inbox_provider_event", "provider", "provider_event_id"),
    )


class OutboxMessage(Base):
    """Outbox messages for idempotency."""

    __tablename__ = "outbox_messages"

    id = Column(Integer, primary_key=True)
    channel = Column(String(20), nullable=False)  # telegram, telnyx
    idempotency_key = Column(String(64), nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(
        String(20), default="pending", nullable=False
    )  # pending, sent, failed
    provider_message_id = Column(String(100), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Unique constraint for idempotency
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_outbox_idempotency"),
        Index("idx_outbox_idempotency", "idempotency_key"),
    )


class ScheduledAction(Base):
    """Scheduled actions for APScheduler."""

    __tablename__ = "scheduled_actions"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # reminder, call_retry, etc.
    run_at = Column(DateTime, nullable=False)
    state = Column(
        String(20), default="pending", nullable=False
    )  # pending, running, completed, failed
    payload_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    incident = relationship("Incident", back_populates="scheduled_actions")

    # Indexes
    __table_args__ = (Index("idx_scheduled_actions_run_at", "run_at"),)
