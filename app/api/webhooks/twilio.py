"""Twilio webhook handlers for panic session voice calls and SMS responses."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.panic_session_service import PanicSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/twilio", tags=["twilio-webhooks"])


@router.post("/panic-call/{session_id}/{guardian_id}")
async def handle_panic_call_response(
    session_id: str,
    guardian_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    CallSid: str = Form(None),
    CallStatus: str = Form(None),
    Digits: str = Form(None),
):
    """Handle DTMF responses during panic voice calls."""

    try:
        logger.info(
            f"Panic call response: session={session_id}, guardian={guardian_id}, digits={Digits}, status={CallStatus}"
        )

        # Initialize panic service
        panic_service = PanicSessionService(db)

        if Digits == "1":
            # Positive acknowledgment
            await panic_service.handle_guardian_response(
                session_id=UUID(session_id),
                guardian_id=UUID(guardian_id),
                response_type="positive",
                response_method="voice",
            )

            twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you. The user has been notified that you will assist. Please contact them as soon as possible.</Say>
    <Hangup/>
</Response>"""

        elif Digits == "0":
            # Negative response
            await panic_service.handle_guardian_response(
                session_id=UUID(session_id),
                guardian_id=UUID(guardian_id),
                response_type="negative",
                response_method="voice",
            )

            twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Understood. You have been excluded from this alert cycle. Other guardians are being contacted.</Say>
    <Hangup/>
</Response>"""

        else:
            # No digits or invalid response - play prompt
            webhook_url = f"/webhooks/twilio/panic-call/{session_id}/{guardian_id}"

            twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Emergency alert. A user needs your help. Press 1 if you can assist, or press 0 if you cannot help.</Say>
    <Gather numDigits="1" timeout="10" action="{webhook_url}">
        <Say voice="alice">Press 1 to help, or 0 if you cannot assist.</Say>
    </Gather>
    <Say voice="alice">No response received. Other guardians are being contacted. Goodbye.</Say>
    <Hangup/>
</Response>"""

        return Response(content=twiml_response, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling panic call response: {e}")

        # Return error TwiML
        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, there was an error processing your response. Please contact the user directly.</Say>
    <Hangup/>
</Response>"""

        return Response(content=error_twiml, media_type="application/xml")


@router.post("/panic-sms/{session_id}/{guardian_id}")
async def handle_panic_sms_response(
    session_id: str,
    guardian_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    MessageSid: str = Form(None),
    MessageStatus: str = Form(None),
    Body: str = Form(None),
):
    """Handle SMS responses to panic alerts."""

    try:
        logger.info(
            f"Panic SMS response: session={session_id}, guardian={guardian_id}, body={Body}, status={MessageStatus}"
        )

        # Initialize panic service
        panic_service = PanicSessionService(db)

        if Body:
            body_clean = Body.strip().lower()

            if body_clean == "1":
                # Positive acknowledgment
                await panic_service.handle_guardian_response(
                    session_id=UUID(session_id),
                    guardian_id=UUID(guardian_id),
                    response_type="positive",
                    response_method="sms",
                )

                logger.info(
                    f"Guardian {guardian_id} acknowledged session {session_id} via SMS"
                )

            elif body_clean == "0":
                # Negative response
                await panic_service.handle_guardian_response(
                    session_id=UUID(session_id),
                    guardian_id=UUID(guardian_id),
                    response_type="negative",
                    response_method="sms",
                )

                logger.info(
                    f"Guardian {guardian_id} declined session {session_id} via SMS"
                )

            else:
                logger.info(
                    f"Invalid SMS response '{Body}' from guardian {guardian_id} for session {session_id}"
                )

        # Twilio expects a 200 response for SMS webhooks
        return {"status": "received"}

    except Exception as e:
        logger.error(f"Error handling panic SMS response: {e}")
        raise HTTPException(status_code=500, detail="Error processing SMS response")


# Legacy webhook endpoints for backward compatibility (if needed)
@router.post("/voice")
async def handle_legacy_voice_webhook(request: Request):
    """Legacy voice webhook - redirects to new panic-specific endpoints."""
    return Response(
        content="""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">This endpoint is deprecated. Please use the panic-specific voice endpoints.</Say>
    <Hangup/>
</Response>""",
        media_type="application/xml",
    )


@router.post("/sms")
async def handle_legacy_sms_webhook(request: Request):
    """Legacy SMS webhook - for backward compatibility."""
    return {"status": "deprecated", "message": "Use panic-specific SMS endpoints"}
