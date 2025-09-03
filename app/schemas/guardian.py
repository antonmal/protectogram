from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.user import Gender


class GuardianBase(BaseModel):
    telegram_user_id: Optional[int] = Field(
        None, description="Telegram user ID for sending messages"
    )
    phone_number: str = Field(..., description="Phone number with country code")
    name: str = Field(..., min_length=1, max_length=100)
    gender: Gender

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if not v:
            return v

        # Normalize: remove spaces, dashes, parentheses
        normalized = (
            v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )

        # Ensure it starts with +
        if not normalized.startswith("+"):
            if normalized.startswith("00"):
                normalized = "+" + normalized[2:]
            elif normalized.isdigit() and len(normalized) >= 8:
                raise ValueError(
                    "Phone number must include country code (start with +)"
                )
            else:
                normalized = "+" + normalized

        # Basic validation: 8-20 digits after +
        if len(normalized) < 8 or len(normalized) > 20:
            raise ValueError("Phone number must be 8-20 digits")

        if not normalized[1:].isdigit():
            raise ValueError("Phone number can only contain digits after +")

        return normalized


class GuardianCreate(GuardianBase):
    pass


class GuardianUpdate(BaseModel):
    telegram_user_id: Optional[int] = None
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if not v:
            return v

        # Normalize: remove spaces, dashes, parentheses
        normalized = (
            v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )

        # Ensure it starts with +
        if not normalized.startswith("+"):
            if normalized.startswith("00"):
                normalized = "+" + normalized[2:]
            elif normalized.isdigit() and len(normalized) >= 8:
                raise ValueError(
                    "Phone number must include country code (start with +)"
                )
            else:
                normalized = "+" + normalized

        # Basic validation: 8-20 digits after +
        if len(normalized) < 8 or len(normalized) > 20:
            raise ValueError("Phone number must be 8-20 digits")

        if not normalized[1:].isdigit():
            raise ValueError("Phone number can only contain digits after +")

        return normalized


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
