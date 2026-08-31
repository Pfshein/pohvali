"""Create the star ledger and balance tables.

Revision ID: 20260901_0003
Revises: 20260901_0002
Create Date: 2026-09-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0003"
down_revision: str | Sequence[str] | None = "20260901_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "star_ledger",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_star_ledger_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_star_ledger")),
    )
    op.create_index(
        "uq_star_ledger_daily_per_day",
        "star_ledger",
        ["user_id", "local_date"],
        unique=True,
        postgresql_where=sa.text("reason = 'daily'"),
    )

    op.create_table(
        "star_balances",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "balance",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "balance >= 0",
            name=op.f("ck_star_balances_balance_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_star_balances_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_star_balances")),
    )


def downgrade() -> None:
    op.drop_table("star_balances")
    op.drop_index("uq_star_ledger_daily_per_day", table_name="star_ledger")
    op.drop_table("star_ledger")
