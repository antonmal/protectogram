import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import models and settings using factory pattern
from app.config.settings import SettingsFactory
from app.models import Base

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings factory
environment = os.getenv("ENVIRONMENT", "development")
settings = SettingsFactory.create(environment)
# Use sync URL for migrations (remove +asyncpg)
database_url = settings.database_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """Only include objects that are part of our application models."""
    # Ignore PostGIS and TIGER geocoder tables
    if type_ == "table" and name in [
        "zip_lookup",
        "tabblock20",
        "cousub",
        "addrfeat",
        "zcta5",
        "featnames",
        "place",
        "pagc_rules",
        "zip_lookup_base",
        "place_lookup",
        "zip_state_loc",
        "pagc_gaz",
        "tabblock",
        "bg",
        "direction_lookup",
        "secondary_unit_lookup",
        "layer",
        "faces",
        "topology",
        "addr",
        "county",
        "street_type_lookup",
        "loader_variables",
        "state",
        "loader_lookuptables",
        "zip_state",
        "tract",
        "county_lookup",
        "state_lookup",
        "zip_lookup_all",
        "spatial_ref_sys",
        "countysub_lookup",
        "geocode_settings",
        "pagc_lex",
        "loader_platform",
        "edges",
        "geocode_settings_default",
    ]:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
