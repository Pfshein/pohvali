"""Add last reminded local date to reminder state.

Revision ID: 20260901_0009
Revises: 20260901_0008
Create Date: 2026-09-01 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0009"
down_revision: str | Sequence[str] | None = "20260901_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reminder_states",
        sa.Column("last_reminded_on", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reminder_states", "last_reminded_on")
