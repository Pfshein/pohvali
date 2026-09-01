"""Add threshold-based mascot unlocks.

Revision ID: 20260901_0006
Revises: 20260901_0005
Create Date: 2026-09-01 12:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0006"
down_revision: str | Sequence[str] | None = "20260901_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("mascots", sa.Column("unlock_threshold", sa.Integer(), nullable=True))
    op.create_check_constraint(
        op.f("ck_mascots_unlock_threshold_positive"),
        "mascots",
        "unlock_threshold IS NULL OR unlock_threshold > 0",
    )
    op.create_unique_constraint(
        op.f("uq_mascots_unlock_threshold"),
        "mascots",
        ["unlock_threshold"],
    )
    op.execute("UPDATE mascots SET unlock_threshold = 10 WHERE code = 'tisha'")
    op.execute("UPDATE mascots SET unlock_threshold = 30 WHERE code = 'lumi'")
    op.execute("UPDATE mascots SET unlock_threshold = 100 WHERE code = 'bim'")

    op.create_table(
        "mascot_unlocks",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mascot_code", sa.String(length=32), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["mascot_code"],
            ["mascots.code"],
            name=op.f("fk_mascot_unlocks_mascot_code_mascots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_mascot_unlocks_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "mascot_code", name=op.f("pk_mascot_unlocks")),
    )


def downgrade() -> None:
    op.drop_table("mascot_unlocks")
    op.drop_constraint(op.f("uq_mascots_unlock_threshold"), "mascots", type_="unique")
    op.drop_constraint(
        op.f("ck_mascots_unlock_threshold_positive"),
        "mascots",
        type_="check",
    )
    op.drop_column("mascots", "unlock_threshold")
