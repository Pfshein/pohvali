from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserActivityDay(Base):
    """One opaque daily activity marker per user and UTC day."""

    __tablename__ = "user_activity_days"
    __table_args__ = (
        CheckConstraint("open_count > 0", name="open_count_positive"),
        Index("ix_user_activity_days_activity_date", "activity_date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity_date: Mapped[date] = mapped_column(Date, primary_key=True)
    first_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    open_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
