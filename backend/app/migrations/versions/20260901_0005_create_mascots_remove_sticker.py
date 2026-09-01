"""Create mascot catalog and remove the unused praise sticker field.

Revision ID: 20260901_0005
Revises: 20260901_0004
Create Date: 2026-09-01 11:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0005"
down_revision: str | Sequence[str] | None = "20260901_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    mascots = op.create_table(
        "mascots",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("blurb", sa.String(length=160), nullable=False),
        sa.Column("asset_path", sa.String(length=160), nullable=False),
        sa.Column("starter", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_mascots")),
        sa.UniqueConstraint("asset_path", name=op.f("uq_mascots_asset_path")),
    )
    op.bulk_insert(
        mascots,
        [
            {
                "code": "ava",
                "name": "Авокадо Ава",
                "blurb": "Спокойная и тёплая",
                "asset_path": "/assets/mascots/ava.png",
                "starter": True,
                "sort_order": 10,
                "active": True,
            },
            {
                "code": "pol",
                "name": "Пингвин Поль",
                "blurb": "Неспешный и уютный",
                "asset_path": "/assets/mascots/pol.png",
                "starter": True,
                "sort_order": 20,
                "active": True,
            },
            {
                "code": "mira",
                "name": "Кошка Мира",
                "blurb": "Мягкая и внимательная",
                "asset_path": "/assets/mascots/mira.png",
                "starter": True,
                "sort_order": 30,
                "active": True,
            },
            {
                "code": "tisha",
                "name": "Капибара Тиша",
                "blurb": "Добрая и невозмутимая",
                "asset_path": "/assets/mascots/tisha.png",
                "starter": False,
                "sort_order": 40,
                "active": True,
            },
            {
                "code": "lumi",
                "name": "Облачко Луми",
                "blurb": "Лёгкое и заботливое",
                "asset_path": "/assets/mascots/lumi.png",
                "starter": False,
                "sort_order": 50,
                "active": True,
            },
            {
                "code": "bim",
                "name": "Лягушонок Бим",
                "blurb": "Тихий и любопытный",
                "asset_path": "/assets/mascots/bim.png",
                "starter": False,
                "sort_order": 60,
                "active": True,
            },
        ],
    )
    op.drop_column("praises", "sticker")


def downgrade() -> None:
    op.add_column("praises", sa.Column("sticker", sa.String(length=32), nullable=True))
    op.drop_table("mascots")
