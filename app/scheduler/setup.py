"""APScheduler setup with Postgres job store."""

from datetime import UTC, datetime, timedelta
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging import get_logger
from app.scheduler.jobs import handle_scheduled_action

logger = get_logger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def get_jobstore_url() -> str:
    """Get jobstore URL from Postgres URL."""
    # Convert asyncpg URL to psycopg2 URL for APScheduler
    url = settings.POSTGRES_URL
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


async def setup_scheduler() -> None:
    """Setup APScheduler with Postgres job store."""
    global scheduler

    if scheduler is not None:
        logger.info("Scheduler already initialized")
        return

    # Check if scheduler is enabled
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled by configuration")
        return

    try:
        # Configure job store
        jobstore = SQLAlchemyJobStore(url=get_jobstore_url())

        # Create scheduler
        scheduler = AsyncIOScheduler(
            jobstores={"default": jobstore},
            job_defaults={
                "coalesce": False,
                "max_instances": 1,
                "misfire_grace_time": 60,  # 1 minute grace time
            },
            timezone="UTC",
        )

        # Start scheduler
        scheduler.start()
        logger.info("APScheduler started successfully")

        # Add a test job to verify scheduler is working
        test_job_id = "test_scheduler"
        if not scheduler.get_job(test_job_id):
            scheduler.add_job(
                func=test_scheduler_job,
                trigger="date",
                run_date=datetime.now(UTC) + timedelta(seconds=5),
                id=test_job_id,
                replace_existing=True,
            )
            logger.info("Added test scheduler job")

    except Exception as e:
        logger.error("Failed to setup scheduler", error=str(e))
        raise


async def test_scheduler_job() -> None:
    """Test job to verify scheduler is working."""
    logger.info("Test scheduler job executed successfully")


async def schedule_action(
    incident_id: int,
    action_type: str,
    run_at: datetime,
    payload: dict[str, Any] | None = None,
) -> str:
    """Schedule an action for an incident."""
    if scheduler is None:
        raise RuntimeError("Scheduler not initialized")

    job_id = f"{action_type}_{incident_id}_{run_at.timestamp()}"

    scheduler.add_job(
        func=handle_scheduled_action,
        trigger="date",
        run_date=run_at,
        id=job_id,
        args=[incident_id, action_type, payload],
        replace_existing=True,
    )

    logger.info(
        "Scheduled action",
        job_id=job_id,
        incident_id=incident_id,
        action_type=action_type,
        run_at=run_at.isoformat(),
    )

    return job_id


async def cancel_incident_jobs(incident_id: int) -> None:
    """Cancel all scheduled jobs for an incident."""
    if scheduler is None:
        return

    jobs_to_remove = []
    for job in scheduler.get_jobs():
        if job.args and len(job.args) > 0 and job.args[0] == incident_id:
            jobs_to_remove.append(job.id)

    for job_id in jobs_to_remove:
        scheduler.remove_job(job_id)
        logger.info("Cancelled job", job_id=job_id, incident_id=incident_id)


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    if scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return scheduler
