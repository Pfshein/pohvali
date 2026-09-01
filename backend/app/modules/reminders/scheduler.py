"""Evening reminder scheduler (PH-502/PH-503).

A single background job runs every ~10 minutes and drives one reminder delivery
pass: selecting who is due (timezone/DST aware, deduplicated per local day) and
sending or fading them (see ``delivery``). Because this is an in-process
scheduler, the backend must run as a single instance (deploy runbook, PH-705).
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("app.reminders.scheduler")

# A delivery runs one full pass given the session factory and the current UTC
# instant. ``delivery.deliver_reminders`` (bound to a sender) is the production
# implementation; tests substitute their own.
Delivery = Callable[[async_sessionmaker[AsyncSession], datetime], Awaitable[None]]

DEFAULT_INTERVAL_MINUTES = 10
JOB_ID = "reminder-candidates"


async def run_reminder_cycle(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    deliver: Delivery,
    now: datetime | None = None,
) -> None:
    """Run one delivery pass. Never raises, so a bad cycle can't kill the job."""
    moment = now or datetime.now(UTC)
    try:
        await deliver(session_factory, moment)
    except Exception:
        logger.exception("reminder cycle failed")


def build_reminder_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    deliver: Delivery,
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_reminder_cycle,
        trigger="interval",
        minutes=interval_minutes,
        kwargs={"session_factory": session_factory, "deliver": deliver},
        id=JOB_ID,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
