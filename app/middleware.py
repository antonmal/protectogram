"""Custom middleware for Protectogram."""

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import verify_token
from app.config.settings import BaseAppSettings


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that optionally adds user info to request state if JWT token is present.

    This allows endpoints to work both authenticated and unauthenticated,
    but access user info when available.
    """

    def __init__(self, app, settings: BaseAppSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        """Process request and add optional user info."""

        # Try to extract JWT token from Authorization header
        auth_header = request.headers.get("Authorization")
        user_info = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = verify_token(token, self.settings)
                user_info = {
                    "user_id": payload.get("sub"),
                    "telegram_user_id": payload.get("telegram_user_id"),
                    "username": payload.get("username"),
                }
            except Exception:
                # Invalid token - continue without user info
                pass

        # Add user info to request state
        request.state.user_info = user_info

        # Continue with request
        response = await call_next(request)
        return response


def get_optional_user_info(request: Request) -> Optional[dict]:
    """
    Get user info from request state if available.

    Returns None if no valid token was provided.
    """
    return getattr(request.state, "user_info", None)
