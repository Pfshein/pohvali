from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reminders import repository as repo
from app.modules.reminders.state import ReminderPhase

# The gentle nudge belongs to the user's local 22:xx hour. Selection runs every
# ~10 minutes (PH-502); the once-per-day guard keeps the six runs of that hour
# from sending more than one push.
REMINDER_HOUR = 22


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


@dataclass(frozen=True, slots=True)
class ReminderCandidate:
    user_id: UUID
    telegram_id: int
    local_date: date


def _local_now(timezone: str, moment: datetime) -> datetime | None:
    try:
        return moment.astimezone(ZoneInfo(timezone))
    except (ZoneInfoNotFoundError, ValueError):
        return None


async def select_reminder_candidates(
    session: AsyncSession,
    *,
    now: datetime,
) -> list[ReminderCandidate]:
    """Users who should receive an evening nudge at ``now`` (a UTC instant).

    A candidate is opted in, reachable, still ``active``, currently inside their
    local 22:xx hour (IANA/DST aware), has not been reminded yet on that local
    date, and has not written a praise today.
    """
    rows = await repo.list_reminder_eligible(session)

    in_window: list[ReminderCandidate] = []
    for row in rows:
        local = _local_now(row.timezone, now)
        if local is None or local.hour != REMINDER_HOUR:
            continue
        local_date = local.date()
        if row.last_reminded_on == local_date:
            continue
        in_window.append(
            ReminderCandidate(
                user_id=row.id,
                telegram_id=row.telegram_id,
                local_date=local_date,
            )
        )

    if not in_window:
        return []

    already_wrote = await repo.praises_written_on(
        session,
        pairs=[(candidate.user_id, candidate.local_date) for candidate in in_window],
    )
    return [
        candidate
        for candidate in in_window
        if (candidate.user_id, candidate.local_date) not in already_wrote
    ]


async def mark_reminded(
    session: AsyncSession,
    *,
    user_id: UUID,
    local_date: date,
) -> None:
    async with session.begin():
        await repo.mark_reminded(session, user_id=user_id, local_date=local_date)


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
