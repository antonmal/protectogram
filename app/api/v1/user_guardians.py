"""User-Guardian relationship management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.dependencies import get_user_guardian_service
from app.models.user import User
from app.schemas.user_guardian import (
    UserGuardianCreate,
    UserGuardianResponse,
    UserGuardianUpdate,
    UserGuardiansListResponse,
)
from app.services.user_guardian import UserGuardianService

router = APIRouter(prefix="/users/{user_id}/guardians", tags=["user-guardians"])


@router.post(
    "/",
    response_model=UserGuardianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a guardian to user",
)
async def add_guardian_to_user(
    user_id: UUID,
    guardian_data: UserGuardianCreate,
    user_guardian_service: Annotated[
        UserGuardianService, Depends(get_user_guardian_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Link a guardian to a user with priority order.

    - **guardian_id**: UUID of the guardian to link
    - **priority_order**: Priority order for alerts (1 = first to contact)

    **Note**: Users can only manage their own guardians. Priority conflicts
    are resolved automatically by shifting other guardians' priorities.
    """
    # Verify user can only manage their own guardians
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own guardians",
        )

    try:
        user_guardian = await user_guardian_service.add_guardian_to_user(
            user_id, guardian_data
        )
        # Reload with guardian data
        guardians = await user_guardian_service.get_user_guardians(user_id)
        for ug in guardians:
            if ug.id == user_guardian.id:
                return UserGuardianResponse.model_validate(ug)
        return UserGuardianResponse.model_validate(user_guardian)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{guardian_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove guardian from user",
)
async def remove_guardian_from_user(
    user_id: UUID,
    guardian_id: UUID,
    user_guardian_service: Annotated[
        UserGuardianService, Depends(get_user_guardian_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Remove a guardian from user's list and reorder priorities."""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own guardians",
        )

    success = await user_guardian_service.remove_guardian_from_user(
        user_id, guardian_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardian relationship not found",
        )


@router.put(
    "/{guardian_id}/priority",
    response_model=UserGuardianResponse,
    summary="Update guardian priority",
)
async def update_guardian_priority(
    user_id: UUID,
    guardian_id: UUID,
    update_data: UserGuardianUpdate,
    user_guardian_service: Annotated[
        UserGuardianService, Depends(get_user_guardian_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update guardian priority order. Other guardians' priorities are adjusted automatically."""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage your own guardians",
        )

    user_guardian = await user_guardian_service.update_guardian_priority(
        user_id, guardian_id, update_data
    )
    if not user_guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guardian relationship not found",
        )

    # Reload with guardian data
    guardians = await user_guardian_service.get_user_guardians(user_id)
    for ug in guardians:
        if ug.id == user_guardian.id:
            return UserGuardianResponse.model_validate(ug)
    return UserGuardianResponse.model_validate(user_guardian)


@router.get(
    "/", response_model=UserGuardiansListResponse, summary="List user's guardians"
)
async def get_user_guardians(
    user_id: UUID,
    user_guardian_service: Annotated[
        UserGuardianService, Depends(get_user_guardian_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get user's guardians ordered by priority.

    **Note**: Users can only view their own guardians.
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own guardians",
        )

    guardians = await user_guardian_service.get_user_guardians(user_id)
    total = await user_guardian_service.count_user_guardians(user_id)

    return UserGuardiansListResponse(
        guardians=[UserGuardianResponse.model_validate(ug) for ug in guardians],
        total=total,
    )
