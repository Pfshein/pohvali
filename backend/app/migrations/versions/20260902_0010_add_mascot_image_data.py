"""Add mascot image bytes for admin-added mascots.

Revision ID: 20260902_0010
Revises: 20260901_0009
Create Date: 2026-09-02 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0010"
down_revision: str | Sequence[str] | None = "20260901_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mascots",
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mascots", "image_data")
