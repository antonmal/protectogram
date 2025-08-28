"""Access control for E.164 phone number allowlist."""

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def is_phone_number_allowed(phone_number: str) -> bool:
    """
    Check if a phone number is allowed to use the application.

    Args:
        phone_number: E.164 formatted phone number (e.g., "+1234567890")

    Returns:
        True if the phone number is allowed, False otherwise
    """
    # If allowlist is disabled, allow all numbers
    if not settings.FEATURE_ALLOW_ONLY_WHITELIST:
        logger.debug(
            "Access control disabled, allowing phone number", phone_number=phone_number
        )
        return True

    # If no allowlist configured, deny all numbers
    if not settings.ALLOWED_E164_NUMBERS:
        logger.warning("Access control enabled but no allowlist configured")
        return False

    # Normalize phone number to E.164 format
    normalized_number = normalize_e164(phone_number)

    # Get allowed numbers from configuration
    allowed_numbers = get_allowed_numbers()

    # Check if number is in allowlist
    is_allowed = normalized_number in allowed_numbers

    logger.info(
        "Phone number access check",
        phone_number=normalized_number,
        is_allowed=is_allowed,
        allowlist_enabled=settings.FEATURE_ALLOW_ONLY_WHITELIST,
    )

    return is_allowed


def normalize_e164(phone_number: str) -> str:
    """
    Normalize phone number to E.164 format.

    Args:
        phone_number: Phone number in any format

    Returns:
        E.164 formatted phone number
    """
    # Remove all non-digit characters except +
    cleaned = "".join(c for c in phone_number if c.isdigit() or c == "+")

    # Ensure it starts with +
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def get_allowed_numbers() -> list[str]:
    """
    Get the list of allowed E.164 phone numbers from configuration.

    Returns:
        List of normalized E.164 phone numbers
    """
    if not settings.ALLOWED_E164_NUMBERS:
        return []

    # Split comma-separated list and normalize each number
    raw_numbers = [num.strip() for num in settings.ALLOWED_E164_NUMBERS.split(",")]
    normalized_numbers = [normalize_e164(num) for num in raw_numbers if num]

    return normalized_numbers


def get_decline_message() -> str:
    """
    Get the Russian decline message for unauthorized users.

    Returns:
        Russian decline message
    """
    return (
        "🚫 Извини, сейчас Protectogram доступен по приглашению. "
        "Если хочешь участвовать — напиши нам, и мы включим твой номер."
    )
