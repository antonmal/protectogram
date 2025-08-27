import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.storage.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL in order of precedence:
    1. CLI argument: -x db_url=...
    2. Environment variable: ALEMBIC_DATABASE_URL
    3. Config file: sqlalchemy.url (fallback only)
    """
    # Check CLI argument first
    cli_args = context.get_x_argument(as_dictionary=True)
    if cli_args.get("db_url"):
        return cli_args["db_url"]

    # Check environment variable
    env_url = os.environ.get("ALEMBIC_DATABASE_URL")
    if env_url:
        return env_url

    # Fallback to config file (not recommended for tests)
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
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
    # Get the database URL
    database_url = get_database_url()

    # Create async engine for SQLAlchemy 2.x
    if database_url.startswith("postgresql://"):
        # Convert to async URL
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        async_url = database_url

    # Create async engine
    connectable = create_async_engine(
        async_url,
        poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    # Run migrations with async engine
    import asyncio

    asyncio.run(connectable.run_sync(do_run_migrations))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
