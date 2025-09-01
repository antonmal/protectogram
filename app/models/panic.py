"""Panic model for panic button events."""

from sqlalchemy import Column, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class PanicStatus(enum.Enum):
    """Panic event status enumeration."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"


class Panic(BaseModel):
    """Panic model for tracking panic button events."""

    __tablename__ = "panic_events"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to user who triggered panic",
    )

    triggered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the panic button was triggered",
    )

    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the panic was resolved (if applicable)",
    )

    status: PanicStatus = Column(
        SQLEnum(PanicStatus),
        nullable=False,
        default=PanicStatus.ACTIVE,
        index=True,
        comment="Current status of panic event",
    )

    # Relationships
    user = relationship("User", back_populates="panic_events")

    def __repr__(self):
        return f"<Panic(id={self.id}, user_id={self.user_id}, status={self.status.value}, triggered_at={self.triggered_at})>"
