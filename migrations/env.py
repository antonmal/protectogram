import os
from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def normalize_asyncpg_url(raw: str) -> tuple[str, dict]:
    """
    Returns (url, connect_args) suitable for asyncpg.
    - Converts postgres:// → postgresql+asyncpg://
    - Sets ssl=disable for Fly internal hosts (*.internal or fdaa:)
    - Sets ssl=require otherwise
    """
    # driver
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    parts = urlsplit(raw)
    host = parts.hostname or ""
    q = dict(parse_qsl(parts.query, keep_blank_values=True))

    is_internal = host.endswith(".internal") or host.startswith("fdaa:")
    if is_internal:
        q["ssl"] = "disable"
        connect_args = {}  # no SSL for internal
    else:
        q["ssl"] = "require"
        connect_args = {"ssl": "require"}  # asyncpg accepts this

    raw = urlunsplit(parts._replace(query=urlencode(q)))
    return raw, connect_args


def get_database_url() -> str:
    """Get database URL in order of precedence:
    1. CLI argument: -x db_url=...
    2. Environment variable: ALEMBIC_DATABASE_URL
    3. Config file: sqlalchemy.url (fallback only)
    """
    # Check CLI argument first
    cli_args = context.get_x_argument(as_dictionary=True)
    db_url = (
        cli_args.get("db_url")
        or os.environ.get("ALEMBIC_DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    return db_url


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
    # Get the database URL and normalize for asyncpg
    database_url = get_database_url()
    db_url, connect_args = normalize_asyncpg_url(database_url)

    # Create async engine for SQLAlchemy 2.x
    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    async def do_run_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    # Run migrations with async engine
    import asyncio

    async def run_async_migrations():
        async with connectable.begin() as connection:
            await do_run_migrations(connection)

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
