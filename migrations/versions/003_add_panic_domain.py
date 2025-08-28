"""Add panic domain fields and constraints.

Revision ID: 003
Revises: 002
Create Date: 2025-08-28 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
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

    # Add created_at to member_links table (for priority ordering)
    op.add_column(
        "member_links",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Add amd_result to call_attempts table
    op.add_column(
        "call_attempts", sa.Column("amd_result", sa.String(50), nullable=True)
    )

    # Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("traveler_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "acknowledged",
                "canceled",
                "exhausted",
                name="incident_status",
            ),
            nullable=False,
        ),
        sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("ack_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["traveler_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add UNIQUE constraint: only one active incident per ward
    op.create_unique_constraint(
        "uq_incidents_active_per_ward",
        "incidents",
        ["traveler_user_id"],
        postgresql_where=sa.text("status = 'active'"),
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
    op.drop_constraint("uq_incidents_active_per_ward", "incidents", type_="unique")

    # Drop incidents table
    op.drop_table("incidents")

    # Drop incident_status enum
    op.execute("DROP TYPE incident_status")

    # Drop columns
    op.drop_column("call_attempts", "amd_result")
    op.drop_column("member_links", "created_at")
    op.drop_column("users", "preferred_locale")
