"""Twilio webhook handlers for voice calls and SMS responses."""

import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import PanicNotificationAttempt
from app.services.panic_service import PanicAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio-webhooks"])


@router.post("/voice")
async def handle_voice_webhook(
    request: Request,
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    Digits: str = Form(None),
    From: str = Form(...),
    To: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Twilio voice call webhooks for DTMF responses."""

    try:
        logger.info(
            f"Voice webhook: CallSid={CallSid}, Status={CallStatus}, Digits={Digits}"
        )

        # Find the latest notification attempt by provider_id (CallSid)
        query = (
            select(PanicNotificationAttempt)
            .where(PanicNotificationAttempt.provider_id == CallSid)
            .order_by(PanicNotificationAttempt.sent_at.desc())
        )
        result = await db.execute(query)
        attempt = result.scalars().first()

        panic_service = PanicAlertService(db)

        logger.info(
            f"Processing voice webhook: CallSid={CallSid}, Status={CallStatus}, From={From}, To={To}"
        )

        # If no notification attempt found, this might be the initial call setup
        # Return TwiML to gather digits immediately
        if not attempt:
            logger.info(
                f"No notification attempt found for CallSid {CallSid}, returning gather TwiML"
            )
            return Response(
                content=_twiml_gather(
                    "Emergency alert! Press 1 to confirm you can help, or press 9 if this is a false alarm."
                ),
                media_type="application/xml",
            )

        # Handle DTMF input (digits pressed)
        if Digits:
            logger.info(f"DTMF received: {Digits} for CallSid {CallSid}")
            # Guardian pressed a digit
            if Digits == "1":
                # Positive acknowledgment
                logger.info(
                    f"Processing positive acknowledgment from CallSid {CallSid}"
                )
                await panic_service.acknowledge_alert(
                    alert_id=attempt.panic_alert_id,
                    guardian_id=attempt.guardian_id,
                    response="positive",
                )
                logger.info(
                    f"Panic alert {attempt.panic_alert_id} acknowledged positively"
                )
                return Response(
                    content=_twiml_say(
                        "Thank you. The alert has been acknowledged. Help is on the way."
                    ),
                    media_type="application/xml",
                )

            elif Digits == "9":
                # Negative acknowledgment (false alarm)
                logger.info(
                    f"Processing negative acknowledgment from CallSid {CallSid}"
                )
                await panic_service.acknowledge_alert(
                    alert_id=attempt.panic_alert_id,
                    guardian_id=attempt.guardian_id,
                    response="negative",
                )
                logger.info(
                    f"Panic alert {attempt.panic_alert_id} marked as false alarm"
                )
                return Response(
                    content=_twiml_say(
                        "Thank you. The alert has been marked as a false alarm."
                    ),
                    media_type="application/xml",
                )

            else:
                # Invalid digit
                logger.info(f"Invalid DTMF digit received: {Digits}")
                return Response(
                    content=_twiml_gather(
                        "Invalid input. Press 1 to confirm emergency or 9 for false alarm."
                    ),
                    media_type="application/xml",
                )

        # Handle different call statuses
        if CallStatus == "completed":
            logger.info(f"Call {CallSid} completed without DTMF input")

        elif CallStatus in ["no-answer", "busy", "failed"]:
            # Update attempt status
            attempt.status = CallStatus.replace("-", "_")
            await db.commit()
            logger.info(f"Call attempt {CallSid} status updated to: {CallStatus}")

        elif CallStatus in ["in-progress", "answered"]:
            # Call was answered, prompt for input
            return Response(
                content=_twiml_gather(
                    "Emergency alert! Press 1 to confirm you can help, or press 9 if this is a false alarm."
                ),
                media_type="application/xml",
            )

        return Response(content=_twiml_empty(), media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling voice webhook: {e}")
        return Response(
            content=_twiml_say("Sorry, there was an error processing your response."),
            media_type="application/xml",
        )


@router.post("/sms")
async def handle_sms_webhook(
    request: Request,
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    Body: str = Form(None),
    From: str = Form(...),
    To: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Twilio SMS webhook for delivery status and responses."""

    try:
        logger.info(
            f"SMS webhook: MessageSid={MessageSid}, Status={MessageStatus}, Body={Body}"
        )

        # Find the latest notification attempt by provider_id (MessageSid)
        query = (
            select(PanicNotificationAttempt)
            .where(PanicNotificationAttempt.provider_id == MessageSid)
            .order_by(PanicNotificationAttempt.sent_at.desc())
        )
        result = await db.execute(query)
        attempt = result.scalars().first()

        if not attempt:
            logger.warning(
                f"No notification attempt found for MessageSid: {MessageSid}"
            )
            return {"status": "ok"}

        # Update delivery status
        if MessageStatus in ["delivered", "sent", "failed", "undelivered"]:
            attempt.status = MessageStatus
            await db.commit()
            logger.info(f"SMS attempt {MessageSid} status updated to: {MessageStatus}")

        # Handle SMS responses if body contains a response
        if Body and Body.strip():
            body_lower = Body.strip().lower()
            panic_service = PanicAlertService(db)

            if body_lower in ["1", "yes", "ok", "help"]:
                # Positive acknowledgment
                await panic_service.acknowledge_alert(
                    alert_id=attempt.panic_alert_id,
                    guardian_id=attempt.guardian_id,
                    response="positive",
                )
                logger.info(
                    f"Panic alert {attempt.panic_alert_id} acknowledged via SMS"
                )

            elif body_lower in ["9", "no", "false", "alarm"]:
                # Negative acknowledgment
                await panic_service.acknowledge_alert(
                    alert_id=attempt.panic_alert_id,
                    guardian_id=attempt.guardian_id,
                    response="negative",
                )
                logger.info(
                    f"Panic alert {attempt.panic_alert_id} marked as false alarm via SMS"
                )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error handling SMS webhook: {e}")
        return {"status": "error", "message": str(e)}


def _twiml_gather(message: str) -> str:
    """Generate TwiML with Gather for digit input."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" timeout="10" action="https://08c079e98aea.ngrok-free.app/webhooks/twilio/voice" method="POST">
        <Say voice="alice">{message}</Say>
    </Gather>
    <Say voice="alice">No input received. Goodbye.</Say>
</Response>"""


def _twiml_say(message: str) -> str:
    """Generate TwiML with just a message."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{message}</Say>
</Response>"""


def _twiml_empty() -> str:
    """Generate empty TwiML response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
</Response>"""
