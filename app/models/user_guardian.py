"""UserGuardian association model for many-to-many relationship."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserGuardian(BaseModel):
    """Association table for User-Guardian many-to-many relationship with priority."""

    __tablename__ = "user_guardians"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to user",
    )

    guardian_id = Column(
        UUID(as_uuid=True),
        ForeignKey("guardians.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to guardian",
    )

    priority_order = Column(
        Integer,
        nullable=False,
        comment="Priority order for alert sequence (1 = first to contact)",
    )

    # Relationships
    user = relationship("User", back_populates="user_guardians")
    guardian = relationship("Guardian", back_populates="user_guardians")

    def __repr__(self):
        return f"<UserGuardian(user_id={self.user_id}, guardian_id={self.guardian_id}, priority={self.priority_order})>"
