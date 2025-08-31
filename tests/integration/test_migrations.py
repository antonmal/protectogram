"""Integration tests for database migrations."""

import os

import pytest
import sqlalchemy as sa


@pytest.mark.integration
def test_migrations_head_applied():
    """Test that migrations are applied to the test database."""
    url = os.getenv("APP_DATABASE_URL_SYNC")
    assert url, "APP_DATABASE_URL_SYNC not set"

    engine = sa.create_engine(url, future=True)
    with engine.connect() as conn:
        # Check that expected tables exist
        inspector = sa.inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = ["inbox_events", "outbox_messages"]
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"

    engine.dispose()
