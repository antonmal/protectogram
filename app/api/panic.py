"""API endpoints for panic alert functionality."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.panic import (
    PanicAlertCreate,
    PanicAlertResponse,
    PanicAlertAcknowledge,
    PanicAlertList,
)
from app.services.panic_service import PanicAlertService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/panic", tags=["panic"])


@router.post("/trigger", response_model=PanicAlertResponse)
async def trigger_panic_alert(
    panic_data: PanicAlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new panic alert."""

    try:
        panic_service = PanicAlertService(db)

        panic_alert = await panic_service.trigger_panic_alert(
            user_id=current_user.id,
            location=panic_data.location,
            message=panic_data.message,
        )

        logger.info(
            f"Panic alert triggered by user {current_user.id}: {panic_alert.id}"
        )

        return PanicAlertResponse.from_orm(panic_alert)

    except Exception as e:
        logger.error(f"Failed to trigger panic alert for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger panic alert",
        )


@router.post("/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_panic_alert(
    alert_id: UUID,
    ack_data: PanicAlertAcknowledge,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a panic alert (for guardians)."""

    try:
        panic_service = PanicAlertService(db)

        # TODO: Verify that current_user is a guardian of the alert user
        # For now, we'll use current_user.id as guardian_id

        success = await panic_service.acknowledge_alert(
            alert_id=alert_id,
            guardian_id=current_user.id,  # This should be guardian ID
            response=ack_data.response,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Panic alert not found or cannot be acknowledged",
            )

        logger.info(f"Panic alert {alert_id} acknowledged by {current_user.id}")

        return {"message": "Panic alert acknowledged successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge panic alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge panic alert",
        )


@router.post("/{alert_id}/retry", response_model=dict)
async def retry_panic_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually retry a panic alert."""

    try:
        panic_service = PanicAlertService(db)

        # TODO: Verify that current_user owns the alert

        success = await panic_service.retry_alert(alert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Panic alert not found or cannot be retried",
            )

        logger.info(f"Panic alert {alert_id} retried by {current_user.id}")

        return {"message": "Panic alert retry initiated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry panic alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry panic alert",
        )


@router.post("/{alert_id}/resolve", response_model=dict)
async def resolve_panic_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually resolve a panic alert."""

    try:
        panic_service = PanicAlertService(db)

        # TODO: Verify that current_user owns the alert

        success = await panic_service.resolve_alert(alert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Panic alert not found"
            )

        logger.info(f"Panic alert {alert_id} resolved by {current_user.id}")

        return {"message": "Panic alert resolved"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve panic alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve panic alert",
        )


@router.get("/alerts", response_model=PanicAlertList)
async def get_user_panic_alerts(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get panic alerts for the current user."""

    try:
        panic_service = PanicAlertService(db)

        alerts = await panic_service.get_user_alerts(
            user_id=current_user.id, status=status, limit=limit
        )

        return PanicAlertList(
            alerts=[PanicAlertResponse.from_orm(alert) for alert in alerts],
            total=len(alerts),
        )

    except Exception as e:
        logger.error(f"Failed to get panic alerts for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve panic alerts",
        )


@router.get("/{alert_id}", response_model=PanicAlertResponse)
async def get_panic_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific panic alert."""

    try:
        panic_service = PanicAlertService(db)

        # Get user's alerts and find the specific one
        alerts = await panic_service.get_user_alerts(
            user_id=current_user.id,
            limit=1000,  # Get all to find specific alert
        )

        alert = next((a for a in alerts if a.id == alert_id), None)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Panic alert not found"
            )

        return PanicAlertResponse.from_orm(alert)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get panic alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve panic alert",
        )
