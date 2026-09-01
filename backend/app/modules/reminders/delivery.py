"""Reminder delivery and fade (PH-503).

Turns the reminder state of every reachable user into concrete evening actions
and carries them out:

- ``DAILY``   — an active user gets the 22:xx nudge.
- ``FADE``    — an active user ignored their previous push (no praise on the
                reminded local date), so they step down to ``dormant`` — no
                message is sent.
- ``RETURN``  — a user dormant for ``DORMANT_TO_SILENT_DAYS`` gets exactly one
                calm return message, then goes ``silent``.

Silent users, users already acted on today, and users who wrote today are left
alone. Re-engagement (writing a praise) resets the fade to ``active`` elsewhere
(``repository.reactivate_on_praise``). Sends honour Telegram throttling with
backoff, and state only advances after a send succeeds so a throttled push is
retried on the next cycle rather than lost.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.bot.messages import REMINDER_NUDGE, REMINDER_RETURN
from app.modules.reminders import repository as repo
from app.modules.reminders.sender import ReminderSender, ReminderThrottled
from app.modules.reminders.service import REMINDER_HOUR, local_now
from app.modules.reminders.state import DORMANT_TO_SILENT_DAYS, ReminderPhase

logger = logging.getLogger("app.reminders.delivery")

MAX_SEND_ATTEMPTS = 3

DAILY = "daily"
RETURN = "return"
FADE = "fade"

_MESSAGES = {DAILY: REMINDER_NUDGE, RETURN: REMINDER_RETURN}


@dataclass(frozen=True, slots=True)
class ReminderAction:
    user_id: UUID
    telegram_id: int
    local_date: date
    kind: str


async def plan_reminder_actions(
    session: AsyncSession,
    *,
    now: datetime,
) -> list[ReminderAction]:
    """Decide the evening action for each reachable user at ``now`` (UTC)."""
    rows = await repo.list_reminder_pending(session)

    pending: list[tuple] = []
    date_pairs: set[tuple[UUID, date]] = set()
    for row in rows:
        local = local_now(row.timezone, now)
        if local is None or local.hour != REMINDER_HOUR:
            continue
        local_date = local.date()
        if row.last_reminded_on == local_date:
            continue  # already acted on this local day
        pending.append((row, local_date))
        date_pairs.add((row.id, local_date))
        if row.phase == ReminderPhase.ACTIVE.value and row.last_reminded_on is not None:
            date_pairs.add((row.id, row.last_reminded_on))

    if not pending:
        return []

    written = await repo.praises_written_on(session, pairs=list(date_pairs))

    actions: list[ReminderAction] = []
    for row, local_date in pending:
        if (row.id, local_date) in written:
            continue  # wrote today — engaged, leave them be

        if row.phase == ReminderPhase.ACTIVE.value:
            previous_ignored = (
                row.last_reminded_on is not None
                and row.last_reminded_on < local_date
                and (row.id, row.last_reminded_on) not in written
            )
            kind = FADE if previous_ignored else DAILY
            actions.append(ReminderAction(row.id, row.telegram_id, local_date, kind))
        elif row.phase == ReminderPhase.DORMANT.value:
            if now - row.phase_changed_at >= timedelta(days=DORMANT_TO_SILENT_DAYS):
                actions.append(
                    ReminderAction(row.id, row.telegram_id, local_date, RETURN)
                )

    return actions


async def send_with_backoff(
    sender: ReminderSender,
    *,
    chat_id: int,
    text: str,
    sleep: Callable[[float], Awaitable[None]],
    attempts: int = MAX_SEND_ATTEMPTS,
) -> bool:
    """Send once, backing off on Telegram throttling. Returns whether it sent."""
    for attempt in range(attempts):
        try:
            await sender(chat_id=chat_id, text=text)
            return True
        except ReminderThrottled as throttled:
            if attempt == attempts - 1:
                return False
            await sleep(throttled.retry_after)
    return False


async def deliver_reminders(
    session_factory: async_sessionmaker[AsyncSession],
    now: datetime | None = None,
    *,
    sender: ReminderSender,
    sleep: Callable[[float], Awaitable[None]],
) -> None:
    """Plan and execute one delivery pass. Each write uses its own transaction."""
    moment = now or datetime.now(UTC)

    async with session_factory() as session:
        actions = await plan_reminder_actions(session, now=moment)

    for action in actions:
        if action.kind == FADE:
            async with session_factory() as session, session.begin():
                await repo.advance_phase(
                    session,
                    user_id=action.user_id,
                    phase=ReminderPhase.DORMANT,
                    now=moment,
                    local_date=action.local_date,
                )
            continue

        sent = await send_with_backoff(
            sender,
            chat_id=action.telegram_id,
            text=_MESSAGES[action.kind],
            sleep=sleep,
        )
        if not sent:
            continue  # throttled out; retry next cycle without losing state

        async with session_factory() as session, session.begin():
            if action.kind == RETURN:
                await repo.advance_phase(
                    session,
                    user_id=action.user_id,
                    phase=ReminderPhase.SILENT,
                    now=moment,
                    local_date=action.local_date,
                )
            else:
                await repo.mark_reminded(
                    session, user_id=action.user_id, local_date=action.local_date
                )
