import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

from app.modules.reminders.scheduler import (
    JOB_ID,
    build_reminder_scheduler,
    run_reminder_cycle,
)


def fake_factory() -> object:
    return object()


def test_scheduler_runs_every_ten_minutes() -> None:
    scheduler = build_reminder_scheduler(fake_factory, deliver=AsyncMock())  # type: ignore[arg-type]
    job = scheduler.get_job(JOB_ID)

    assert job is not None
    assert job.trigger.interval == timedelta(minutes=10)


def test_cycle_invokes_delivery_with_the_factory_and_instant() -> None:
    deliver = AsyncMock()
    from datetime import UTC, datetime

    moment = datetime(2026, 9, 1, 19, 15, tzinfo=UTC)
    asyncio.run(run_reminder_cycle(fake_factory, deliver=deliver, now=moment))  # type: ignore[arg-type]

    deliver.assert_awaited_once_with(fake_factory, moment)


def test_cycle_never_raises_when_delivery_fails() -> None:
    deliver = AsyncMock(side_effect=RuntimeError("db down"))

    # Should swallow the error rather than propagate and kill the job.
    asyncio.run(run_reminder_cycle(fake_factory, deliver=deliver))  # type: ignore[arg-type]

    deliver.assert_awaited_once()
