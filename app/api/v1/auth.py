"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import create_user_token, get_current_user
from app.config.settings import BaseAppSettings
from app.dependencies import get_settings, get_user_service
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TelegramLoginRequest(BaseModel):
    """Telegram login request schema."""

    telegram_user_id: int


@router.post(
    "/telegram-login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate via Telegram user ID",
)
async def telegram_login(
    login_request: TelegramLoginRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
):
    """
    Authenticate a user using their Telegram user ID.

    This endpoint is designed for Telegram bot integration where users
    are already authenticated by Telegram's OAuth flow.

    - **telegram_user_id**: The user's Telegram ID

    Returns JWT access token and user information.
    """
    # Find user by Telegram ID
    user = await user_service.get_by_telegram_id(login_request.telegram_user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register first.",
        )

    # Create JWT token
    access_token = create_user_token(user, settings)

    return TokenResponse(
        access_token=access_token, user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Get the current authenticated user's profile.

    Requires valid JWT token in Authorization header:
    ```
    Authorization: Bearer <jwt_token>
    ```
    """
    return UserResponse.model_validate(current_user)
