from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.user import Gender


class GuardianBase(BaseModel):
    telegram_user_id: Optional[int] = Field(
        None, description="Telegram user ID for sending messages"
    )
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")
    name: str = Field(..., min_length=1, max_length=100)
    gender: Gender

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v


class GuardianCreate(GuardianBase):
    pass


class GuardianUpdate(BaseModel):
    telegram_user_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if v and not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v


class GuardianResponse(GuardianBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GuardianListResponse(BaseModel):
    guardians: List[GuardianResponse]
    total: int
    page: int
    per_page: int
