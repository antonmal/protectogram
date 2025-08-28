"""APScheduler runner that blocks indefinitely."""

import asyncio

from app.core.logging import get_logger
from app.scheduler.setup import get_scheduler, setup_scheduler

logger = get_logger(__name__)


async def main():
    """Main scheduler function that blocks indefinitely."""
    try:
        # Setup the scheduler
        await setup_scheduler()

        # Get the scheduler instance
        scheduler = get_scheduler()

        logger.info("Scheduler started successfully, blocking indefinitely")

        # Block indefinitely to keep the process alive
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            # Graceful shutdown
            scheduler.shutdown()
            logger.info("Scheduler shutdown complete")

    except Exception as e:
        logger.error("Fatal error in scheduler", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
