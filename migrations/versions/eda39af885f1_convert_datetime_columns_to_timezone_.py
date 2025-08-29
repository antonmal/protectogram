"""Convert datetime columns to timezone-aware

Revision ID: eda39af885f1
Revises: f705d587bd52
Create Date: 2025-08-27 23:07:49.041085

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eda39af885f1"
down_revision: str | Sequence[str] | None = "f705d587bd52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert datetime columns to timezone-aware timestamps."""
    # Users table
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # MemberLinks table
    op.execute(
        "ALTER TABLE member_links ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE member_links ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # Incidents table
    op.execute(
        "ALTER TABLE incidents ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # Alerts table
    op.execute(
        "ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE alerts ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # InboxEvents table
    op.execute(
        "ALTER TABLE inbox_events ALTER COLUMN received_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE inbox_events ALTER COLUMN processed_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # OutboxMessages table
    op.execute(
        "ALTER TABLE outbox_messages ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE outbox_messages ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # ScheduledActions table
    op.execute(
        "ALTER TABLE scheduled_actions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    """Convert datetime columns back to timezone-naive timestamps."""
    # Users table
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # MemberLinks table
    op.execute(
        "ALTER TABLE member_links ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE member_links ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # Incidents table
    op.execute(
        "ALTER TABLE incidents ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # Alerts table
    op.execute(
        "ALTER TABLE alerts ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE alerts ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # InboxEvents table
    op.execute(
        "ALTER TABLE inbox_events ALTER COLUMN received_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE inbox_events ALTER COLUMN processed_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # OutboxMessages table
    op.execute(
        "ALTER TABLE outbox_messages ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE outbox_messages ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # ScheduledActions table
    op.execute(
        "ALTER TABLE scheduled_actions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE scheduled_actions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # CallAttempts table
    op.execute(
        "ALTER TABLE call_attempts ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE call_attempts ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
