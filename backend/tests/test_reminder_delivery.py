import asyncio

from app.modules.bot.messages import FORBIDDEN_TONE_WORDS, REMINDER_NUDGE, REMINDER_RETURN
from app.modules.reminders.delivery import send_with_backoff
from app.modules.reminders.sender import ReminderThrottled


class FlakySender:
    """Throttles the first ``fail_times`` calls, then succeeds."""

    def __init__(self, fail_times: int, retry_after: float = 1.0) -> None:
        self.fail_times = fail_times
        self.retry_after = retry_after
        self.calls = 0

    async def __call__(self, *, chat_id: int, text: str) -> None:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ReminderThrottled(self.retry_after)


def test_backoff_retries_after_throttling_then_succeeds() -> None:
    sender = FlakySender(fail_times=2)
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    sent = asyncio.run(
        send_with_backoff(sender, chat_id=1, text="hi", sleep=sleep)
    )

    assert sent is True
    assert sender.calls == 3
    assert slept == [1.0, 1.0]  # backed off before each retry


def test_backoff_gives_up_after_the_attempt_budget() -> None:
    sender = FlakySender(fail_times=99)
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    sent = asyncio.run(
        send_with_backoff(sender, chat_id=1, text="hi", sleep=sleep, attempts=3)
    )

    assert sent is False
    assert sender.calls == 3
    assert len(slept) == 2  # no sleep after the final failed attempt


def test_reminder_messages_stay_calm_and_pressure_free() -> None:
    for text in (REMINDER_NUDGE, REMINDER_RETURN):
        lowered = text.casefold()
        for word in FORBIDDEN_TONE_WORDS:
            assert word.casefold() not in lowered
