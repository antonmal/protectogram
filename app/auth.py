"""Authentication utilities for JWT token handling."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config.settings import BaseAppSettings
from app.dependencies import get_settings, get_user_service
from app.models.user import User
from app.services.user import UserService

# Security scheme
security = HTTPBearer()


class AuthenticationError(Exception):
    """Custom authentication error."""

    pass


def create_access_token(
    data: dict, settings: BaseAppSettings, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        settings: Application settings
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default: 24 hours for this security app
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

    return encoded_jwt


def verify_token(token: str, settings: BaseAppSettings) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify
        settings: Application settings

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: BaseAppSettings = Depends(get_settings),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP bearer token
        settings: Application settings
        user_service: User service for database operations

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token
        payload = verify_token(credentials.credentials, settings)

        # Extract user information
        user_id_str: str = payload.get("sub")
        telegram_user_id: int = payload.get("telegram_user_id")

        if user_id_str is None or telegram_user_id is None:
            raise credentials_exception

        user_id = UUID(user_id_str)

    except (JWTError, ValueError, AuthenticationError):
        raise credentials_exception

    # Get user from database
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exception

    # Additional security: verify telegram_user_id matches
    if user.telegram_user_id != telegram_user_id:
        raise credentials_exception

    return user


def create_user_token(user: User, settings: BaseAppSettings) -> str:
    """
    Create a JWT token for a specific user.

    Args:
        user: User to create token for
        settings: Application settings

    Returns:
        JWT access token
    """
    token_data = {
        "sub": str(user.id),
        "telegram_user_id": user.telegram_user_id,
        "username": user.telegram_username,
    }

    return create_access_token(token_data, settings)
