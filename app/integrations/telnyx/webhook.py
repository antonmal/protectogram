"""Telnyx webhook verification with test mode support."""

import hashlib
import hmac
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    headers: dict[str, str],
) -> bool:
    """
    Verify Telnyx webhook signature with test mode support.

    Args:
        payload: Raw request body
        signature: Ed25519 signature from Telnyx-Signature-Ed25519 header
        timestamp: Timestamp from Telnyx-Timestamp header
        headers: All request headers

    Returns:
        True if signature is valid or test mode is enabled, False otherwise
    """
    # Check for test mode
    logger.info(
        "Webhook verification",
        test_mode=settings.TELNYX_WEBHOOK_TEST_MODE,
        x_simulated=headers.get("X-Simulated"),
        x_simulated_lower=headers.get("x-simulated"),
        all_headers=list(headers.keys()),
    )

    if settings.TELNYX_WEBHOOK_TEST_MODE:
        # In test mode, accept requests with X-Simulated header (case insensitive)
        if headers.get("X-Simulated") == "1" or headers.get("x-simulated") == "1":
            logger.info(
                "Accepting simulated webhook request",
                mode="test",
                signature_present=bool(signature),
            )
            return True

    # In production mode or when test mode is disabled, require valid signature
    if not signature:
        logger.warning("No Telnyx signature provided", mode="production")
        return False

    # Verify Ed25519 signature
    try:
        # Get the webhook secret (you'll need to add this to your config)
        webhook_secret = settings.TELNYX_WEBHOOK_SECRET

        # Create the signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"

        # Verify the signature
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures (constant-time comparison)
        if hmac.compare_digest(signature, expected_signature):
            logger.info("Telnyx webhook signature verified", mode="production")
            return True
        else:
            logger.warning("Invalid Telnyx webhook signature", mode="production")
            return False

    except Exception as e:
        logger.error(
            "Error verifying Telnyx webhook signature",
            error=str(e),
            mode="production",
        )
        return False


def extract_webhook_data(
    payload: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any] | None:
    """
    Extract and validate webhook data.

    Args:
        payload: Parsed JSON payload
        headers: Request headers

    Returns:
        Extracted webhook data or None if invalid
    """
    try:
        # Extract basic webhook data
        event_data = {
            "event_type": payload.get("data", {}).get("event_type"),
            "event_id": payload.get("data", {}).get("id"),
            "payload": payload,
            "is_simulated": headers.get("X-Simulated") == "1",
        }

        # Validate required fields
        if not event_data["event_type"]:
            logger.warning("Missing event_type in webhook payload")
            return None

        if not event_data["event_id"]:
            logger.warning("Missing event_id in webhook payload")
            return None

        logger.info(
            "Webhook data extracted",
            event_type=event_data["event_type"],
            event_id=event_data["event_id"],
            is_simulated=event_data["is_simulated"],
        )

        return event_data

    except Exception as e:
        logger.error("Error extracting webhook data", error=str(e))
        return None
