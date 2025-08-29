"""APScheduler setup and configuration."""

from datetime import datetime
from typing import Any

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.observability.metrics import scheduler_job_lag_seconds
from app.scheduler.registry import get_job_function

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call start_scheduler() first.")
    return _scheduler


def _create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    # Get current settings
    from app.core.settings import Settings

    current_settings = Settings()

    # Job store configuration
    jobstores = {
        "default": SQLAlchemyJobStore(
            url=current_settings.app_database_url_sync,
            tablename=current_settings.scheduler_jobstore_table_name,
        )
    }

    # Executor configuration
    executors = {
        "default": AsyncIOExecutor(),
    }

    # Job defaults
    job_defaults = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 60,
    }

    return AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone="UTC",
    )


async def heartbeat_job() -> None:
    """Heartbeat job to monitor scheduler health."""
    scheduler = get_scheduler()
    job = scheduler.get_job("heartbeat")

    if job and job.scheduled_run_time:
        lag_seconds = (datetime.now() - job.scheduled_run_time).total_seconds()
        scheduler_job_lag_seconds.set(lag_seconds)


def register_recurring_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register recurring jobs."""
    # Get current settings
    from app.core.settings import Settings

    current_settings = Settings()

    if current_settings.startup_heartbeat_job_cron:
        scheduler.add_job(
            func=heartbeat_job,
            trigger=CronTrigger.from_crontab(current_settings.startup_heartbeat_job_cron),
            id="heartbeat",
            name="Scheduler Heartbeat",
            replace_existing=True,
        )


async def schedule_one_shot(run_at: datetime, func_name: str, **kwargs: Any) -> str:
    """Schedule a one-shot job."""
    scheduler = get_scheduler()

    # Get the job function from registry
    job_func = get_job_function(func_name)

    job = scheduler.add_job(
        func=job_func,
        trigger="date",
        run_date=run_at,
        kwargs=kwargs,
        id=f"oneshot_{func_name}_{run_at.timestamp()}",
        name=f"One-shot {func_name}",
    )

    return job.id


async def start_scheduler() -> None:
    """Start the scheduler."""
    global _scheduler

    # Check if scheduler is enabled (re-read settings in case env vars changed)
    from app.core.settings import Settings

    current_settings = Settings()

    if not current_settings.scheduler_enabled:
        return

    if _scheduler is not None:
        return  # Already started

    _scheduler = _create_scheduler()
    register_recurring_jobs(_scheduler)
    _scheduler.start()


async def shutdown_scheduler() -> None:
    """Shutdown the scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
