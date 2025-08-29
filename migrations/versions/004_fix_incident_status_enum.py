"""Fix incident_status enum conversion.

Revision ID: 004
Revises: 003
Create Date: 2025-08-29 00:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix incident_status enum conversion."""

    # First, ensure the enum type exists
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE incident_status AS ENUM ('active', 'acknowledged', 'canceled', 'exhausted');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Convert the status column to use the enum
    op.execute("""
        ALTER TABLE incidents 
        ALTER COLUMN status TYPE incident_status 
        USING status::incident_status
    """)


def downgrade() -> None:
    """Revert incident_status enum conversion."""

    # Convert back to VARCHAR
    op.execute("""
        ALTER TABLE incidents 
        ALTER COLUMN status TYPE VARCHAR(20)
    """)

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS incident_status")
