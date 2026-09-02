"""Add server-side user roles.

Revision ID: 20260902_0011
Revises: 20260902_0010
Create Date: 2026-09-02 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0011"
down_revision: str | Sequence[str] | None = "20260902_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), nullable=False, server_default="user"),
    )
    op.create_check_constraint(
        "role_valid",
        "users",
        "role IN ('user', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_role_valid"), "users", type_="check")
    op.drop_column("users", "role")
