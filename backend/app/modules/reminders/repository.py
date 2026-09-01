from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reminders.models import ReminderState
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
