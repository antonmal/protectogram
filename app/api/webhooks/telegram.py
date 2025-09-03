"""Telegram webhook endpoints for bot integration."""

import logging
from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
import sqlalchemy

from app.dependencies import get_telegram_client, get_telegram_onboarding_service
from app.integrations.telegram_client import TelegramClient
from app.services.telegram_onboarding import TelegramOnboardingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram-webhooks"])


class TelegramWebhookUpdate(BaseModel):
    """Telegram webhook update model."""

    update_id: int
    message: Dict[str, Any] = None
    callback_query: Dict[str, Any] = None
    inline_query: Dict[str, Any] = None


class SetWebhookRequest(BaseModel):
    """Request model for setting webhook URL."""

    webhook_url: str


@router.post(
    "/webhook-test",
    status_code=status.HTTP_200_OK,
    summary="Simple webhook test endpoint",
)
async def telegram_webhook_test(request: Request):
    """Simple test endpoint to debug webhook issues."""
    try:
        update_data = await request.json()
        return {"status": "test_ok", "received": update_data.get("update_id")}
    except Exception as e:
        return {"status": "test_error", "error": str(e)}


@router.post(
    "/test-database", status_code=status.HTTP_200_OK, summary="Test database connection"
)
async def test_database_connection(request: Request):
    """Test if database connection works."""
    import sys

    diagnosis = {}

    # Server environment info
    diagnosis["python_executable"] = sys.executable
    diagnosis["python_path_entries"] = len(sys.path)
    diagnosis["venv_detected"] = "venv" in sys.executable

    # Test 1: Direct greenlet import
    try:
        import greenlet

        diagnosis["greenlet_import"] = "SUCCESS"
        diagnosis["greenlet_version"] = greenlet.__version__
        diagnosis["greenlet_path"] = greenlet.__file__
    except Exception as e:
        diagnosis["greenlet_import"] = f"FAILED: {e}"
        # Try to find where greenlet should be
        try:
            import pkg_resources

            dist = pkg_resources.get_distribution("greenlet")
            diagnosis["greenlet_expected_path"] = dist.location
        except Exception:
            pass

    # Test 2: Manual greenlet installation check
    try:
        import subprocess

        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "greenlet"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            diagnosis["pip_greenlet_status"] = "INSTALLED"
        else:
            diagnosis["pip_greenlet_status"] = "NOT FOUND"
    except Exception as e:
        diagnosis["pip_greenlet_status"] = f"ERROR: {e}"

    # Test 3: Database operations
    try:
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(sqlalchemy.text("SELECT 1"))
            diagnosis["database_operations"] = "SUCCESS"
    except Exception as e:
        diagnosis["database_operations"] = f"FAILED: {e}"

    return {"status": "diagnosis", "results": diagnosis}


@router.post(
    "/test-start-command",
    status_code=status.HTTP_200_OK,
    summary="Test start command directly",
)
async def test_start_command(request: Request):
    """Test the start command handler directly."""
    try:
        # Get client from app state
        telegram_client = request.app.state.telegram_client

        if not telegram_client:
            return {"status": "error", "message": "Telegram client not found"}

        # Count handlers
        handlers_info = []
        for group, handlers_list in telegram_client.application.handlers.items():
            handlers_info.append(f"Group {group}: {len(handlers_list)} handlers")
            for i, handler in enumerate(handlers_list):
                handlers_info.append(f"  - {type(handler).__name__}")

        return {
            "status": "ok",
            "bot_ready": telegram_client.is_ready(),
            "handlers": handlers_info,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post(
    "/webhook", status_code=status.HTTP_200_OK, summary="Telegram bot webhook endpoint"
)
async def telegram_webhook(
    request: Request,
    telegram_client: Annotated[TelegramClient, Depends(get_telegram_client)],
    onboarding_service: Annotated[
        TelegramOnboardingService, Depends(get_telegram_onboarding_service)
    ],
):
    """
    Handle incoming updates from Telegram via webhook.

    This endpoint receives updates from Telegram's servers when users
    interact with the bot (messages, button clicks, etc.).
    """
    try:
        # Get raw JSON data
        update_data = await request.json()

        logger.info(f"Received Telegram webhook update: {update_data.get('update_id')}")

        # Check if telegram client is available
        if not telegram_client or not telegram_client.is_ready():
            logger.error("Telegram client not ready")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram bot service unavailable",
            )

        # Inject onboarding service into client
        telegram_client.set_onboarding_service(onboarding_service)

        # Process the update
        await telegram_client.process_webhook_update(update_data)

        return {"status": "ok", "message": "Update processed successfully"}

    except Exception as e:
        logger.error(f"Failed to process Telegram webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook update",
        )


@router.get(
    "/health", status_code=status.HTTP_200_OK, summary="Telegram bot health check"
)
async def telegram_health_check(
    telegram_client: Annotated[TelegramClient, Depends(get_telegram_client)],
):
    """Check if the Telegram bot is healthy and ready."""
    if not telegram_client or not telegram_client.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot not ready",
        )

    return {
        "status": "healthy",
        "bot_ready": telegram_client.is_ready(),
        "message": "Telegram bot is operational",
    }


@router.post(
    "/set-webhook", status_code=status.HTTP_200_OK, summary="Set Telegram webhook URL"
)
async def set_telegram_webhook(
    webhook_request: SetWebhookRequest,
    telegram_client: Annotated[TelegramClient, Depends(get_telegram_client)],
):
    """
    Set the webhook URL for the Telegram bot.

    This endpoint allows you to configure where Telegram should send updates.
    Usually called during deployment or configuration.
    """
    if not telegram_client or not telegram_client.bot:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot not ready",
        )

    try:
        # Set webhook
        success = await telegram_client.bot.set_webhook(
            url=webhook_request.webhook_url,
            allowed_updates=["message", "callback_query", "inline_query"],
        )

        if success:
            logger.info(f"Webhook set successfully to: {webhook_request.webhook_url}")
            return {
                "status": "success",
                "webhook_url": webhook_request.webhook_url,
                "message": "Webhook configured successfully",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to set webhook"
            )

    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set webhook: {str(e)}",
        )
