"""Add mascot ownership and active selection.

Revision ID: 20260901_0007
Revises: 20260901_0006
Create Date: 2026-09-01 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0007"
down_revision: str | Sequence[str] | None = "20260901_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mascot_ownership",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mascot_code", sa.String(length=32), nullable=False),
        sa.Column("price_paid", sa.Integer(), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price_paid >= 0", name=op.f("ck_mascot_ownership_price_non_negative")),
        sa.ForeignKeyConstraint(
            ["mascot_code"],
            ["mascots.code"],
            name=op.f("fk_mascot_ownership_mascot_code_mascots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_mascot_ownership_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "mascot_code", name=op.f("pk_mascot_ownership")),
    )

    op.add_column(
        "users",
        sa.Column("active_mascot_code", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_users_active_mascot_code_mascots"),
        "users",
        "mascots",
        ["active_mascot_code"],
        ["code"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_users_active_mascot_code_mascots"),
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "active_mascot_code")
    op.drop_table("mascot_ownership")
