"""Evening reminder scheduler (PH-502).

A single background job runs every ~10 minutes, selects the users who are due
their local 22:xx nudge, and hands them to a candidate handler. Selection is
timezone/DST aware and deduplicated per local day (see ``service``). Sending is
PH-503's job: the default handler here only records how many were selected, so
no Telegram id or message text is ever logged.

Because this is an in-process scheduler, the backend must run as a single
instance (see the deploy runbook, PH-705).
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.reminders.service import ReminderCandidate, select_reminder_candidates

logger = logging.getLogger("app.reminders.scheduler")

CandidateHandler = Callable[[list[ReminderCandidate]], Awaitable[None]]

DEFAULT_INTERVAL_MINUTES = 10
JOB_ID = "reminder-candidates"


async def _log_candidate_count(candidates: list[ReminderCandidate]) -> None:
    if candidates:
        logger.info("reminder candidates selected", extra={"count": len(candidates)})


async def run_reminder_cycle(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    handle: CandidateHandler,
    now: datetime | None = None,
) -> None:
    """Run one selection cycle. Never raises, so a bad cycle can't kill the job."""
    moment = now or datetime.now(UTC)
    try:
        async with session_factory() as session:
            candidates = await select_reminder_candidates(session, now=moment)
        await handle(candidates)
    except Exception:
        logger.exception("reminder cycle failed")


def build_reminder_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    handle: CandidateHandler | None = None,
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_reminder_cycle,
        trigger="interval",
        minutes=interval_minutes,
        kwargs={"session_factory": session_factory, "handle": handle or _log_candidate_count},
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
