"""Telegram security utilities."""

import hmac
import hashlib
from typing import Optional


def verify_telegram_secret(received: Optional[str], expected: str) -> bool:
    """Verify Telegram webhook secret token.
    
    Args:
        received: The secret token from the request header (can be None)
        expected: The expected secret token from environment
        
    Returns:
        True if the secret is valid, False otherwise
        
    Note:
        Uses constant-time comparison to prevent timing attacks.
    """
    if not expected:
        return False
    
    if received is None:
        return False
    
    # Use hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(received, expected)
