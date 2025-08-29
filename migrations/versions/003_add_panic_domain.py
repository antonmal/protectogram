"""Add panic domain fields and constraints.

Revision ID: 003
Revises: 002
Create Date: 2025-08-28 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "eda39af885f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add panic domain fields and constraints."""

    # Add preferred_locale to users table
    op.add_column(
        "users",
        sa.Column(
            "preferred_locale", sa.String(10), nullable=False, server_default="ru-RU"
        ),
    )

    # Add amd_result to call_attempts table
    op.add_column(
        "call_attempts", sa.Column("amd_result", sa.String(50), nullable=True)
    )

    # Add new columns to existing incidents table
    op.add_column(
        "incidents",
        sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # Create incident_status enum
    op.execute(
        "CREATE TYPE incident_status AS ENUM ('active', 'acknowledged', 'canceled', 'exhausted')"
    )

    # Alter incidents.status to use the enum
    op.execute(
        "ALTER TABLE incidents ALTER COLUMN status TYPE incident_status USING status::incident_status"
    )

    # Add UNIQUE constraint: only one active incident per ward
    op.execute(
        "CREATE UNIQUE INDEX uq_incidents_active_per_ward ON incidents (traveler_user_id) WHERE status = 'active'"
    )

    # Create indexes for performance
    op.create_index("ix_incidents_traveler_user_id", "incidents", ["traveler_user_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])
    op.create_index("ix_member_links_created_at", "member_links", ["created_at"])


def downgrade() -> None:
    """Remove panic domain fields and constraints."""

    # Drop indexes
    op.drop_index("ix_member_links_created_at", table_name="member_links")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_traveler_user_id", table_name="incidents")

    # Drop UNIQUE constraint
    op.execute("DROP INDEX IF EXISTS uq_incidents_active_per_ward")

    # Drop columns from incidents table
    op.drop_column("incidents", "exhausted_at")
    op.drop_column("incidents", "updated_at")

    # Revert incidents.status back to string
    op.execute("ALTER TABLE incidents ALTER COLUMN status TYPE VARCHAR(20)")

    # Drop incident_status enum
    op.execute("DROP TYPE incident_status")

    # Drop columns
    op.drop_column("call_attempts", "amd_result")
    op.drop_column("users", "preferred_locale")
