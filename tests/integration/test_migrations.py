"""Test database migrations."""

import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from tests.integration.conftest import PostgresContainerInfo


def test_migrations_create_all_tables(pg_container: PostgresContainerInfo) -> None:
    """Test that migrations create all expected tables."""
    # Set environment variable for Alembic
    os.environ["ALEMBIC_DATABASE_URL"] = pg_container.url_sync

    # Run migrations
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    # Connect to database and verify tables
    engine = create_engine(pg_container.url_sync)
    inspector = inspect(engine)

    # Get all table names
    tables = inspector.get_table_names()

    # Expected tables
    expected_tables = {
        "users",
        "member_links",
        "incidents",
        "alerts",
        "call_attempts",
        "inbox_events",
        "outbox_messages",
        "scheduled_actions",
    }

    assert expected_tables.issubset(set(tables)), f"Missing tables: {expected_tables - set(tables)}"

    # Verify indexes
    with engine.connect() as conn:
        # Check member_links index
        result = conn.execute(
            text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'member_links' 
            AND indexname LIKE '%traveler_user_id%'
        """)
        )
        assert result.fetchone() is not None, "member_links index not found"

        # Check call_attempts index
        result = conn.execute(
            text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'call_attempts' 
            AND indexname LIKE '%alert_id%'
        """)
        )
        assert result.fetchone() is not None, "call_attempts index not found"

        # Check scheduled_actions index
        result = conn.execute(
            text("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'scheduled_actions' 
            AND indexname LIKE '%run_at%'
        """)
        )
        assert result.fetchone() is not None, "scheduled_actions index not found"

        # Check unique constraints
        result = conn.execute(
            text("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'inbox_events'::regclass 
            AND contype = 'u'
        """)
        )
        assert result.fetchone() is not None, "inbox_events unique constraint not found"

        result = conn.execute(
            text("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'outbox_messages'::regclass 
            AND contype = 'u'
        """)
        )
        assert result.fetchone() is not None, "outbox_messages unique constraint not found"

    engine.dispose()


def test_migrations_downgrade(pg_container: PostgresContainerInfo) -> None:
    """Test that migrations can be downgraded."""
    # Set environment variable for Alembic
    os.environ["ALEMBIC_DATABASE_URL"] = pg_container.url_sync

    # Run migrations up
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    # Verify tables exist
    engine = create_engine(pg_container.url_sync)
    inspector = inspect(engine)
    tables_before = inspector.get_table_names()
    assert len(tables_before) > 0, "No tables created"

    # Downgrade one step
    command.downgrade(cfg, "-1")

    # Verify tables are gone (except alembic_version which remains)
    inspector = inspect(engine)
    tables_after = inspector.get_table_names()
    assert tables_after == ["alembic_version"], f"Unexpected tables after downgrade: {tables_after}"

    engine.dispose()
