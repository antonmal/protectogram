"""Guardian management API endpoints."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user
from app.dependencies import get_guardian_service
from app.models.user import User
from app.schemas.guardian import (
    GuardianCreate,
    GuardianListResponse,
    GuardianResponse,
    GuardianUpdate,
)
from app.services.guardian import GuardianService

router = APIRouter(prefix="/guardians", tags=["guardians"])


@router.post(
    "/",
    response_model=GuardianResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new guardian",
)
async def create_guardian(
    guardian_data: GuardianCreate,
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Create a new guardian.

    - **telegram_user_id**: Guardian's Telegram user ID (optional)
    - **phone_number**: Guardian's phone number in E.164 format (required)
    - **name**: Guardian's full name (required)
    - **gender**: Guardian's gender (required)

    **Note**: Requires authentication. Users can create guardians for their own use.
    """
    try:
        guardian = await guardian_service.create(guardian_data)
        return GuardianResponse.model_validate(guardian)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{guardian_id}",
    response_model=GuardianResponse,
    summary="Get guardian by ID",
)
async def get_guardian(
    guardian_id: UUID,
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a specific guardian by their UUID."""
    guardian = await guardian_service.get_by_id(guardian_id)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found"
        )
    return GuardianResponse.model_validate(guardian)


@router.get(
    "/phone/{phone_number}",
    response_model=GuardianResponse,
    summary="Get guardian by phone number",
)
async def get_guardian_by_phone(
    phone_number: str,
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a guardian by their phone number."""
    guardian = await guardian_service.get_by_phone_number(phone_number)
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found"
        )
    return GuardianResponse.model_validate(guardian)


@router.put(
    "/{guardian_id}",
    response_model=GuardianResponse,
    summary="Update guardian",
)
async def update_guardian(
    guardian_id: UUID,
    guardian_data: GuardianUpdate,
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update guardian information."""
    try:
        guardian = await guardian_service.update(guardian_id, guardian_data)
        if not guardian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found"
            )
        return GuardianResponse.model_validate(guardian)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{guardian_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete guardian",
)
async def delete_guardian(
    guardian_id: UUID,
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a guardian (hard delete - removes from database)."""
    success = await guardian_service.delete(guardian_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found"
        )


@router.get(
    "/",
    response_model=GuardianListResponse,
    summary="List guardians",
)
async def list_guardians(
    guardian_service: Annotated[GuardianService, Depends(get_guardian_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or phone number"),
):
    """
    Get a paginated list of guardians with optional search.

    - **page**: Page number (starting from 1)
    - **per_page**: Number of guardians per page (max 100)
    - **search**: Search term to filter by name or phone number (optional)

    **Note**: Requires authentication.
    """
    skip = (page - 1) * per_page

    if search:
        guardians = await guardian_service.search_guardians(
            search_term=search, skip=skip, limit=per_page
        )
        # For search, we'll approximate the total count
        total = (
            len(guardians) + skip
            if len(guardians) == per_page
            else skip + len(guardians)
        )
    else:
        guardians = await guardian_service.list_guardians(skip=skip, limit=per_page)
        total = await guardian_service.count_guardians()

    return GuardianListResponse(
        guardians=[GuardianResponse.model_validate(guardian) for guardian in guardians],
        total=total,
        page=page,
        per_page=per_page,
    )
