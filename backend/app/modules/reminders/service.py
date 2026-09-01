from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reminders import repository as repo
from app.modules.reminders.state import ReminderPhase


class UserNotFound(Exception):
    """The authenticated Telegram id has no stored user (no session opened yet)."""


@dataclass(frozen=True, slots=True)
class ReminderSettings:
    enabled: bool
    dm_available: bool
    phase: ReminderPhase


# Defaults for a user who has never touched reminder state: nudges are on, but
# the bot cannot message them until they open a private chat (`/start`).
_DEFAULTS = ReminderSettings(enabled=True, dm_available=False, phase=ReminderPhase.ACTIVE)


async def record_dm_available(session: AsyncSession, *, telegram_id: int) -> None:
    """Mark that ``/start`` was received, so the bot may message this user.

    Called from the webhook, which may see a user before any Mini App session,
    so the user row is created if missing.
    """
    async with session.begin():
        user_id = await repo.ensure_user_id(session, telegram_id=telegram_id)
        await repo.mark_dm_available(session, user_id=user_id)


async def get_settings(session: AsyncSession, *, telegram_id: int) -> ReminderSettings:
    user = await repo.get_user(session, telegram_id=telegram_id)
    if user is None:
        raise UserNotFound

    state = await repo.get_state(session, user_id=user.id)
    if state is None:
        return _DEFAULTS
    return ReminderSettings(
        enabled=state.enabled,
        dm_available=state.dm_available,
        phase=ReminderPhase(state.phase),
    )


async def set_enabled(
    session: AsyncSession,
    *,
    telegram_id: int,
    enabled: bool,
) -> ReminderSettings:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        await repo.set_enabled(session, user_id=user.id, enabled=enabled)
        state = await repo.get_state(session, user_id=user.id)

    assert state is not None
    return ReminderSettings(
        enabled=state.enabled,
        dm_available=state.dm_available,
        phase=ReminderPhase(state.phase),
    )
