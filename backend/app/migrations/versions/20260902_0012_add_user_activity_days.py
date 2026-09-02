"""Add daily activity markers and indexes used by admin statistics.

Revision ID: 20260902_0012
Revises: 20260902_0011
Create Date: 2026-09-02 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0012"
down_revision: str | Sequence[str] | None = "20260902_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_activity_days",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column(
            "first_opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("open_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_activity_days_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "activity_date", name=op.f("pk_user_activity_days")
        ),
        sa.CheckConstraint(
            "open_count > 0",
            name=op.f("ck_user_activity_days_open_count_positive"),
        ),
    )
    op.create_index(
        op.f("ix_user_activity_days_activity_date"),
        "user_activity_days",
        ["activity_date"],
    )
    op.create_index(op.f("ix_praises_created_at"), "praises", ["created_at"])

    # The historic signal is deliberately limited to dates for which the
    # database has a trustworthy timestamp: account creation and praise rows.
    # It never invents an opening on any other day.
    op.execute(
        sa.text(
            """
            INSERT INTO user_activity_days
                (user_id, activity_date, first_opened_at, last_opened_at, open_count)
            SELECT id, (created_at AT TIME ZONE 'UTC')::date, created_at, created_at, 1
            FROM users
            ON CONFLICT (user_id, activity_date) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO user_activity_days
                (user_id, activity_date, first_opened_at, last_opened_at, open_count)
            SELECT user_id, (created_at AT TIME ZONE 'UTC')::date, created_at, created_at, 1
            FROM praises
            ON CONFLICT (user_id, activity_date) DO UPDATE
            SET first_opened_at = LEAST(
                    user_activity_days.first_opened_at, EXCLUDED.first_opened_at
                ),
                last_opened_at = GREATEST(
                    user_activity_days.last_opened_at, EXCLUDED.last_opened_at
                )
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_praises_created_at"), table_name="praises")
    op.drop_index(op.f("ix_user_activity_days_activity_date"), table_name="user_activity_days")
    op.drop_table("user_activity_days")
