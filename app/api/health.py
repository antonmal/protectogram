"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.observability.metrics import health_ready_checks_total
from app.scheduler.setup import get_scheduler

router = APIRouter()


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Health check endpoint for liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready() -> dict[str, Any]:
    """Health check endpoint for readiness probe."""
    errors = []

    # Check database connectivity
    if not await _check_database():
        errors.append("database_connection_failed")
        health_ready_checks_total.labels(result="fail", reason="database").inc()
    else:
        health_ready_checks_total.labels(result="ok", reason="database").inc()

    # Check scheduler health
    from app.core.settings import Settings

    current_settings = Settings()

    if current_settings.scheduler_enabled:
        if not await _check_scheduler():
            errors.append("scheduler_unhealthy")
            health_ready_checks_total.labels(result="fail", reason="scheduler").inc()
        else:
            health_ready_checks_total.labels(result="ok", reason="scheduler").inc()

    if errors:
        raise HTTPException(status_code=503, detail={"status": "unready", "errors": errors})

    return {"status": "ready"}


async def _check_database() -> bool:
    """Check database connectivity."""
    # Get current settings in case env vars changed
    from app.core.settings import Settings

    current_settings = Settings()

    if not current_settings.app_database_url_sync:
        return False

    try:
        # Create a short-lived engine for the check
        engine = create_engine(
            current_settings.app_database_url_sync,
            pool_pre_ping=True,
            poolclass=None,  # Disable connection pooling for health check
        )

        # Run a simple query with timeout
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        engine.dispose()
        return True

    except SQLAlchemyError:
        return False


async def _check_scheduler() -> bool:
    """Check scheduler health."""
    try:
        scheduler = get_scheduler()

        # Check if scheduler is running
        if not scheduler.running:
            return False

        # Try to access jobstore
        scheduler.get_jobs()
        return True

    except Exception:
        return False
