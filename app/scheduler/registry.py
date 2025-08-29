"""Job registry for one-shot scheduling."""

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Job registry mapping
_job_registry: dict[str, Callable[..., Any]] = {}


def register_job(name: str, func: Callable[..., Any]) -> None:
    """Register a job function."""
    _job_registry[name] = func


def get_job_function(name: str) -> Callable[..., Any]:
    """Get a job function by name."""
    if name not in _job_registry:
        raise ValueError(f"Job '{name}' not found in registry")
    return _job_registry[name]


async def noop_job(**kwargs: Any) -> None:
    """No-op job for testing."""
    logger.info("No-op job executed", extra={"kwargs": kwargs})


async def heartbeat_job(**kwargs: Any) -> None:
    """Heartbeat job for scheduler health monitoring."""
    logger.info("Heartbeat job executed", extra={"kwargs": kwargs})


# Register default jobs
register_job("noop_job", noop_job)
register_job("heartbeat_job", heartbeat_job)
