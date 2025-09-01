"""User model for Protectogram application."""

from sqlalchemy import Column, String, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class Gender(enum.Enum):
    """Gender enumeration."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class User(BaseModel):
    """User model for storing user information."""
    
    __tablename__ = "users"
    
    telegram_user_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="Telegram user ID for bot integration"
    )
    
    phone_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Phone number for SMS/call alerts"
    )
    
    gender = Column(
        SQLEnum(Gender),
        nullable=False,
        comment="User gender"
    )
    
    language = Column(
        String(5),
        nullable=False,
        default="ru",
        comment="User preferred language (ISO 639-1)"
    )
    
    timezone = Column(
        String(50),
        nullable=False,
        default="Europe/Madrid",
        comment="User timezone (tz database name)"
    )
    
    # Relationships
    panic_events = relationship(
        "Panic",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    trips = relationship(
        "Trip",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    user_guardians = relationship(
        "UserGuardian",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_user_id}, phone={self.phone_number})>"