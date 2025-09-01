"""Guardian model for Protectogram application."""

from sqlalchemy import Column, String, BigInteger, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import BaseModel
from .user import Gender


class Guardian(BaseModel):
    """Guardian model for storing guardian information."""
    
    __tablename__ = "guardians"
    
    telegram_user_id = Column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
        comment="Telegram user ID for sending messages to guardian"
    )
    
    phone_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Guardian phone number for SMS/call alerts"
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment="Guardian full name"
    )
    
    gender = Column(
        SQLEnum(Gender),
        nullable=False,
        comment="Guardian gender"
    )
    
    # Relationships
    user_guardians = relationship(
        "UserGuardian",
        back_populates="guardian",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Guardian(id={self.id}, name={self.name}, phone={self.phone_number})>"