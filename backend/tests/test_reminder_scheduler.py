import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, patch

from app.modules.reminders.scheduler import (
    JOB_ID,
    build_reminder_scheduler,
    run_reminder_cycle,
)


class FakeSession:
    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_: object) -> bool:
        return False


def fake_factory() -> FakeSession:
    return FakeSession()


def test_scheduler_runs_every_ten_minutes() -> None:
    scheduler = build_reminder_scheduler(fake_factory)  # type: ignore[arg-type]
    job = scheduler.get_job(JOB_ID)

    assert job is not None
    assert job.trigger.interval == timedelta(minutes=10)


def test_cycle_hands_selected_candidates_to_the_handler() -> None:
    handle = AsyncMock()
    sentinel = ["candidate"]

    with patch(
        "app.modules.reminders.scheduler.select_reminder_candidates",
        new=AsyncMock(return_value=sentinel),
    ):
        asyncio.run(run_reminder_cycle(fake_factory, handle=handle))  # type: ignore[arg-type]

    handle.assert_awaited_once_with(sentinel)


def test_cycle_never_raises_when_selection_fails() -> None:
    handle = AsyncMock()

    with patch(
        "app.modules.reminders.scheduler.select_reminder_candidates",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        asyncio.run(run_reminder_cycle(fake_factory, handle=handle))  # type: ignore[arg-type]

    handle.assert_not_awaited()
