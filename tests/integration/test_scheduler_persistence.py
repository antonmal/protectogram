"""Integration tests for scheduler persistence."""

import os
import pytest
from app.scheduler.setup import start_scheduler, shutdown_scheduler


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduler_persistence():
    """Test that scheduler can persist jobs to the database."""
    # Use the container URLs set by the fixture
    url_sync = os.getenv("APP_DATABASE_URL_SYNC")
    assert url_sync, "APP_DATABASE_URL_SYNC not set"

    # Set environment variables for scheduler
    os.environ["SCHEDULER_ENABLED"] = "true"

    try:
        # Start scheduler
        await start_scheduler()
        
        # Verify scheduler is running
        from app.scheduler.setup import _scheduler
        assert _scheduler.running
        
        # Check that jobs table was created
        import sqlalchemy as sa
        engine = sa.create_engine(url_sync, future=True)
        with engine.connect() as conn:
            inspector = sa.inspect(engine)
            tables = inspector.get_table_names()
            assert "apscheduler_jobs" in tables, "Scheduler jobs table not created"
        
        engine.dispose()
        
    finally:
        # Shutdown scheduler
        await shutdown_scheduler()
        os.environ.pop("SCHEDULER_ENABLED", None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    """Test scheduler startup and shutdown."""
    # Set environment variables for scheduler
    os.environ["SCHEDULER_ENABLED"] = "true"

    try:
        # Start scheduler
        await start_scheduler()
        
        # Verify scheduler is running
        from app.scheduler.setup import _scheduler
        assert _scheduler.running
        
        # Shutdown scheduler
        await shutdown_scheduler()
        
        # Verify scheduler is stopped
        assert not _scheduler.running
        
    finally:
        os.environ.pop("SCHEDULER_ENABLED", None)
