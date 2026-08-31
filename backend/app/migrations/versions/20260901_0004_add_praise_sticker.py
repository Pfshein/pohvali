"""Add a nullable sticker code to praises.

Revision ID: 20260901_0004
Revises: 20260901_0003
Create Date: 2026-09-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0004"
down_revision: str | Sequence[str] | None = "20260901_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("praises", sa.Column("sticker", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("praises", "sticker")
