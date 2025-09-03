from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.guardian import GuardianResponse


class UserGuardianCreate(BaseModel):
    guardian_id: UUID = Field(..., description="Guardian UUID to link")
    priority_order: int = Field(
        ..., ge=1, description="Priority order (1 = first to contact)"
    )


class UserGuardianUpdate(BaseModel):
    priority_order: int = Field(
        ..., ge=1, description="New priority order (1 = first to contact)"
    )


class UserGuardianResponse(BaseModel):
    id: UUID
    user_id: UUID
    guardian_id: UUID
    priority_order: int
    created_at: datetime
    updated_at: datetime
    guardian: GuardianResponse

    class Config:
        from_attributes = True


class UserGuardiansListResponse(BaseModel):
    guardians: List[UserGuardianResponse]
    total: int
