"""Alembic environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url() -> str:
    """Get database URL from environment variables.

    Alembic will use ALEMBIC_DATABASE_URL if set, otherwise APP_DATABASE_URL_SYNC.
    If neither is set, raises RuntimeError with a clear message.
    """
    # Check for Alembic override first
    alembic_url = os.environ.get("ALEMBIC_DATABASE_URL")
    if alembic_url:
        return alembic_url

    # Fall back to sync URL
    sync_url = os.environ.get("APP_DATABASE_URL_SYNC")
    if sync_url:
        return sync_url

    raise RuntimeError(
        "No database URL found. Set either ALEMBIC_DATABASE_URL or APP_DATABASE_URL_SYNC "
        "environment variable."
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=None,  # Will be set in run_migrations_online
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Import here to avoid import-time database connections
    from app.storage import models  # noqa: F401 (ensure mappers are imported)
    from app.storage.base import Base

    target_metadata = Base.metadata

    url = get_url()
    engine = create_engine(url, future=True, pool_pre_ping=True)

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=False,
            dialect_opts={"paramstyle": "named"},
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
