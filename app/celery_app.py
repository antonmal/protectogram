"""
Celery configuration for Protectogram v3.1.
Uses Settings Factory for environment-specific configuration.
"""

import os
from celery import Celery
from app.config.settings import get_cached_settings


def create_celery_app(environment: str | None = None) -> Celery:
    """
    Create Celery app with environment-specific settings.

    Args:
        environment: Target environment. If None, uses ENVIRONMENT env var.

    Returns:
        Configured Celery application instance.
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # Get environment-specific settings
    settings = get_cached_settings(environment)

    # Create Celery app
    celery_app = Celery("protectogram")

    # Configure with settings
    celery_config = settings.get_celery_config()
    celery_app.config_from_object(celery_config, namespace="")

    # Additional configuration
    celery_app.conf.update(
        # Task routing - separate queues for different contexts
        task_routes={
            "app.tasks.panic_alerts.*": {"queue": "panic_alerts"},
            "app.tasks.panic_notifications.*": {"queue": "panic_alerts"},
            "app.tasks.trip_reminders.*": {"queue": "trip_reminders"},
            "app.tasks.notifications.*": {"queue": "notifications"},
            "app.tasks.cleanup.*": {"queue": "cleanup"},
        },
        # Task priorities
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
    )

    # Import all task modules to register them
    celery_app.autodiscover_tasks(
        [
            "app.tasks.panic_alerts",
            "app.tasks.panic_notifications",
            "app.tasks.trip_reminders",
            "app.tasks.notifications",
            "app.tasks.cleanup",
        ]
    )

    return celery_app


# Create default celery app instance
celery_app = create_celery_app()


# Celery task decorators with proper context separation
def panic_task(*args, **kwargs):
    """Decorator for panic-specific tasks."""
    kwargs.setdefault("bind", True)
    kwargs.setdefault("max_retries", 5)
    kwargs.setdefault("default_retry_delay", 60)
    return celery_app.task(*args, **kwargs)


def trip_task(*args, **kwargs):
    """Decorator for trip-specific tasks."""
    kwargs.setdefault("bind", True)
    kwargs.setdefault("max_retries", 3)
    kwargs.setdefault("default_retry_delay", 30)
    return celery_app.task(*args, **kwargs)


def notification_task(*args, **kwargs):
    """Decorator for general notification tasks."""
    kwargs.setdefault("bind", True)
    kwargs.setdefault("max_retries", 3)
    kwargs.setdefault("default_retry_delay", 10)
    return celery_app.task(*args, **kwargs)


# Celery CLI integration
if __name__ == "__main__":
    celery_app.start()
