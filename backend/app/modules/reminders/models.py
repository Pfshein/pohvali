from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.reminders.state import ReminderPhase


class ReminderState(Base):
    """Per-user evening reminder state (PH-501).

    One row per user. ``enabled`` is the user's own opt-out; ``dm_available``
    records whether the person has ever opened a private chat with the bot
    (set on ``/start``), which Telegram requires before the bot may message
    them. ``phase`` follows the documented fade in ``state.py``.
    """

    __tablename__ = "reminder_states"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    dm_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    phase: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ReminderPhase.ACTIVE.value,
        server_default=text("'active'"),
    )
    phase_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    # The user's local date on which a reminder was last sent. Guards
    # "one local day never gets two pushes" during candidate selection (PH-502).
    last_reminded_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
