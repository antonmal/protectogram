"""User management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_user_service
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Register a new user in the system.

    - **telegram_user_id**: Unique Telegram user ID (required)
    - **telegram_username**: Telegram username (optional)
    - **first_name**: User's first name (required)
    - **last_name**: User's last name (optional)
    - **email**: User's email address (optional)
    - **phone_number**: Phone number in E.164 format (optional)
    - **preferred_language**: Language preference (en/ru/es, default: en)
    - **gender**: User's gender (optional)
    """
    try:
        user = await user_service.create(user_data)
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
)
async def get_user(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Get a specific user by their UUID."""
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.from_orm(user)


@router.get(
    "/telegram/{telegram_user_id}",
    response_model=UserResponse,
    summary="Get user by Telegram ID",
)
async def get_user_by_telegram_id(
    telegram_user_id: int,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Get a user by their Telegram user ID."""
    user = await user_service.get_by_telegram_id(telegram_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.from_orm(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Update user information."""
    user = await user_service.update(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.from_orm(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
)
async def delete_user(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    """Delete a user (hard delete - removes from database)."""
    success = await user_service.delete(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
)
async def list_users(
    user_service: Annotated[UserService, Depends(get_user_service)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    Get a paginated list of users.

    - **page**: Page number (starting from 1)
    - **per_page**: Number of users per page (max 100)
    """
    skip = (page - 1) * per_page

    users = await user_service.list_users(skip=skip, limit=per_page)
    total = await user_service.count_users()

    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        per_page=per_page,
    )
