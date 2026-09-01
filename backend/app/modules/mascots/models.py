from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Mascot(Base):
    __tablename__ = "mascots"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    blurb: Mapped[str] = mapped_column(String(160), nullable=False)
    asset_path: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unlock_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "unlock_threshold IS NULL OR unlock_threshold > 0",
            name="unlock_threshold_positive",
        ),
    )


class MascotUnlock(Base):
    __tablename__ = "mascot_unlocks"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mascot_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("mascots.code", ondelete="CASCADE"),
        primary_key=True,
    )
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MascotOwnership(Base):
    """A mascot a user has acquired by spending stars.

    Starter mascots are free and owned implicitly, so they never get a row here;
    only purchased (non-starter) mascots are recorded. `price_paid` keeps the star
    cost at purchase time for an auditable, append-only ownership trail.
    """

    __tablename__ = "mascot_ownership"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mascot_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("mascots.code", ondelete="CASCADE"),
        primary_key=True,
    )
    price_paid: Mapped[int] = mapped_column(Integer, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("price_paid >= 0", name="price_non_negative"),
    )
