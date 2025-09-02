from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.user import Gender


class UserBase(BaseModel):
    telegram_user_id: int = Field(..., description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    preferred_language: str = Field("en", pattern=r"^(en|ru|es)$")
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


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    telegram_username: Optional[str] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(
        None, description="Phone number with country code"
    )
    preferred_language: Optional[str] = Field(None, pattern=r"^(en|ru|es)$")
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


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
