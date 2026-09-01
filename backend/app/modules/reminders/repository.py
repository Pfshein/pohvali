from datetime import date
from uuid import UUID

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.praises.models import Praise
from app.modules.reminders.models import ReminderState
from app.modules.reminders.state import ReminderPhase
from app.modules.users.models import User


async def get_user(session: AsyncSession, *, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def ensure_user_id(session: AsyncSession, *, telegram_id: int) -> UUID:
    """Return the user's id, creating a minimal row on first ``/start``.

    A ``/start`` can arrive before any Mini App session, so the user row may
    not exist yet. Insert leaves ``timezone`` at its safe ``UTC`` default and
    never overwrites an existing row (so a real timezone set later survives).
    """

    await session.execute(
        insert(User)
        .values(telegram_id=telegram_id)
        .on_conflict_do_nothing(index_elements=["telegram_id"])
    )
    result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    return result.scalar_one()


async def mark_dm_available(session: AsyncSession, *, user_id: UUID) -> None:
    """Record that the user has an open private chat with the bot."""
    await session.execute(
        insert(ReminderState)
        .values(user_id=user_id, dm_available=True)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"dm_available": True, "updated_at": func.now()},
        )
    )


async def set_enabled(session: AsyncSession, *, user_id: UUID, enabled: bool) -> None:
    await session.execute(
        insert(ReminderState)
        .values(user_id=user_id, enabled=enabled)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"enabled": enabled, "updated_at": func.now()},
        )
    )


async def get_state(session: AsyncSession, *, user_id: UUID) -> ReminderState | None:
    result = await session.execute(
        select(ReminderState).where(ReminderState.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_reminder_eligible(session: AsyncSession) -> list[Row]:
    """Users who can receive the evening nudge: opted in, reachable, still active.

    Returns lightweight rows (user id, Telegram id, timezone, last reminded
    local date). Timezone/DST and the once-per-day guard are applied by the
    service against each user's wall clock.
    """
    result = await session.execute(
        select(
            User.id,
            User.telegram_id,
            User.timezone,
            ReminderState.last_reminded_on,
        )
        .join(ReminderState, ReminderState.user_id == User.id)
        .where(
            ReminderState.enabled.is_(True),
            ReminderState.dm_available.is_(True),
            ReminderState.phase == ReminderPhase.ACTIVE.value,
        )
    )
    return list(result.all())


async def praises_written_on(
    session: AsyncSession,
    *,
    pairs: list[tuple[UUID, date]],
) -> set[tuple[UUID, date]]:
    """Which of the given (user_id, local_date) pairs already have a praise."""
    if not pairs:
        return set()
    result = await session.execute(
        select(Praise.user_id, Praise.local_date).where(
            tuple_(Praise.user_id, Praise.local_date).in_(pairs)
        )
    )
    return {(row.user_id, row.local_date) for row in result.all()}


async def mark_reminded(
    session: AsyncSession,
    *,
    user_id: UUID,
    local_date: date,
) -> None:
    await session.execute(
        update(ReminderState)
        .where(ReminderState.user_id == user_id)
        .values(last_reminded_on=local_date, updated_at=func.now())
    )
