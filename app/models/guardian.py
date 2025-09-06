"""Guardian model for Protectogram application."""

from sqlalchemy import Column, String, BigInteger, Enum as SQLEnum, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel
from .user import Gender


class Guardian(BaseModel):
    """Guardian model for storing guardian information."""

    __tablename__ = "guardians"

    # Basic Info
    name = Column(String(100), nullable=False, comment="Guardian full name")
    gender: Gender = Column(SQLEnum(Gender), nullable=False, comment="Guardian gender")

    phone_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Guardian phone number for SMS/call alerts",
    )

    # Telegram Integration
    telegram_user_id = Column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
        comment="Telegram user ID for sending messages to guardian",
    )

    telegram_chat_id = Column(
        BigInteger,
        nullable=True,
        index=True,
        comment="Telegram chat ID for sending messages to guardian",
    )

    telegram_username = Column(
        String(100),
        nullable=True,
        comment="Telegram username if available",
    )

    # Registration & Consent
    invitation_token = Column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
        comment="Unique invitation token for registration",
    )

    invited_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When invitation was sent",
    )

    registered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When guardian completed registration",
    )

    consent_given = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether guardian has given explicit consent",
    )

    verification_status = Column(
        String(30),
        default="pending",
        nullable=False,
        comment="Verification status: pending, telegram_verified, phone_verified, fully_verified, declined",
    )

    invitation_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When invitation token expires (7 days from creation)",
    )

    # Contact Preferences
    preferred_contact_method = Column(
        String(20),
        default="both",
        comment="Preferred contact method: phone, telegram, both",
    )

    # Relationships
    user_guardians = relationship(
        "UserGuardian", back_populates="guardian", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Guardian(id={self.id}, name={self.name}, phone={self.phone_number})>"
