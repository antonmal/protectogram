"""Pydantic schemas for panic alert functionality."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PanicAlertCreate(BaseModel):
    """Schema for creating a panic alert."""

    location: Optional[str] = Field(
        None, max_length=500, description="User's current location"
    )
    message: Optional[str] = Field(
        None, max_length=1000, description="Optional message from user"
    )


class PanicAlertAcknowledge(BaseModel):
    """Schema for acknowledging a panic alert."""

    response: str = Field(
        ..., pattern="^(positive|negative)$", description="Guardian response"
    )


class PanicNotificationAttemptResponse(BaseModel):
    """Schema for notification attempt response."""

    id: UUID
    method: str
    status: str
    provider_id: Optional[str]
    response: Optional[str]
    error_message: Optional[str]
    sent_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


class PanicAlertResponse(BaseModel):
    """Schema for panic alert response."""

    id: UUID
    status: str
    location: Optional[str]
    message: Optional[str]
    created_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_response: Optional[str]
    cascade_timeout_at: Optional[datetime]
    retry_count: int
    notification_attempts: List[PanicNotificationAttemptResponse] = []

    class Config:
        from_attributes = True


class PanicAlertList(BaseModel):
    """Schema for list of panic alerts."""

    alerts: List[PanicAlertResponse]
    total: int
