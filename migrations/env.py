import asyncio
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


# --- STRICT DB URL SOURCE ORDER ---
# 1) -x db_url=... (CLI override)
# 2) ALEMBIC_DATABASE_URL (env)
# 3) sqlalchemy.url from alembic.ini (fallback; we will normalize it too)


def _normalize_asyncpg_url(raw: str) -> tuple[str, dict]:
    """
    Normalize any Postgres URL for SQLAlchemy+asyncpg and remove sslmode:
    - postgres:// → postgresql+asyncpg://
    - postgresql:// → postgresql+asyncpg://
    - If host is private (*.internal or fdaa:), enforce ssl=disable and empty connect_args
    - Else enforce ssl=require (URL param) and connect_args={"ssl": "require"}
    - Remove any 'sslmode' from query entirely (asyncpg doesn't accept it)
    """
    if not raw:
        raise RuntimeError(
            "Database URL is empty for Alembic. Set ALEMBIC_DATABASE_URL or pass -x db_url=..."
        )

    # driver normalization
    if raw.startswith("postgres://"):
        raw = "postgresql+asyncpg://" + raw[len("postgres://") :]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]

    parts = urlsplit(raw)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))

    # remove sslmode completely
    if "sslmode" in q:
        q.pop("sslmode", None)

    host = (parts.hostname or "").lower()
    is_internal = host.endswith(".internal") or host.startswith("fdaa:")

    if is_internal:
        q["ssl"] = "disable"
        connect_args = {}
    else:
        q["ssl"] = "require"
        connect_args = {"ssl": "require"}

    # rebuild query
    raw = urlunsplit(parts._replace(query=urlencode(q)))

    return raw, connect_args


def _get_db_url_and_args() -> tuple[str, dict]:
    x = context.get_x_argument(as_dictionary=True) or {}
    raw = (
        x.get("db_url")
        or os.getenv("ALEMBIC_DATABASE_URL")
        or context.config.get_main_option("sqlalchemy.url")
    )
    url, connect_args = _normalize_asyncpg_url(raw)
    return url, connect_args


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
    db_url, connect_args = _get_db_url_and_args()

    connectable = create_async_engine(
        db_url,
        pool_pre_ping=True,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async def do_run_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations():
        async with connectable.begin() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
