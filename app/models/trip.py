"""Trip model for trip tracking functionality."""

from sqlalchemy import Column, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class TripStatus(enum.Enum):
    """Trip status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"  # During panic scenarios
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class Trip(BaseModel):
    """Trip model for tracking user trips."""
    
    __tablename__ = "trips"
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to user making the trip"
    )
    
    expected_arrival_time = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Expected arrival time for the trip"
    )
    
    status = Column(
        SQLEnum(TripStatus),
        nullable=False,
        default=TripStatus.ACTIVE,
        index=True,
        comment="Current status of the trip"
    )
    
    # Relationships
    user = relationship("User", back_populates="trips")
    
    def __repr__(self):
        return f"<Trip(id={self.id}, user_id={self.user_id}, status={self.status.value}, eta={self.expected_arrival_time})>"