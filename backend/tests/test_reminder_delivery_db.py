import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.bot.messages import REMINDER_NUDGE, REMINDER_RETURN
from app.modules.praises.service import create_praise
from app.modules.reminders.delivery import deliver_reminders
from app.modules.reminders.repository import advance_phase, get_user, mark_reminded
from app.modules.reminders.service import get_settings, record_dm_available
from app.modules.reminders.state import ReminderPhase
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TELEGRAM_IDS = tuple(9_503_000 + n for n in range(10))

# Moscow (UTC+3): 22:15 local == 19:15 UTC on 2026-09-01.
NOW = datetime(2026, 9, 1, 19, 15, tzinfo=UTC)
TODAY = date(2026, 9, 1)
YESTERDAY = date(2026, 8, 31)


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def __call__(self, *, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


class ThrottlingSender:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, *, chat_id: int, text: str) -> None:
        from app.modules.reminders.sender import ReminderThrottled

        self.calls += 1
        raise ReminderThrottled(0.0)


async def noop_sleep(_: float) -> None:
    return None


async def cleanup(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:ids)"),
                {"ids": list(TELEGRAM_IDS)},
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    asyncio.run(cleanup(url))
    yield url
    asyncio.run(cleanup(url))


async def make_active(factory: async_sessionmaker, telegram_id: int) -> None:
    async with factory() as session:
        await open_session(session, telegram_id=telegram_id, timezone="Europe/Moscow")
    async with factory() as session:
        await record_dm_available(session, telegram_id=telegram_id)


async def user_id_of(factory: async_sessionmaker, telegram_id: int):
    async with factory() as session:
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        return user.id


async def phase_of(factory: async_sessionmaker, telegram_id: int) -> ReminderPhase:
    async with factory() as session:
        return (await get_settings(session, telegram_id=telegram_id)).phase


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_active_user_gets_one_nudge_and_stops_repeating(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[0]
            await make_active(factory, user)
            sender = FakeSender()

            await deliver_reminders(factory, NOW, sender=sender, sleep=noop_sleep)
            assert (user, REMINDER_NUDGE) in sender.sent
            assert await phase_of(factory, user) is ReminderPhase.ACTIVE

            # A second pass the same local day sends nothing more.
            sender2 = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender2, sleep=noop_sleep)
            assert all(chat_id != user for chat_id, _ in sender2.sent)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_ignored_push_fades_to_dormant_without_sending(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[1]
            await make_active(factory, user)
            # Reminded yesterday, no praise written that day → the push was ignored.
            uid = await user_id_of(factory, user)
            async with factory() as session, session.begin():
                await mark_reminded(session, user_id=uid, local_date=YESTERDAY)

            sender = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender, sleep=noop_sleep)

            assert all(chat_id != user for chat_id, _ in sender.sent)  # no message
            assert await phase_of(factory, user) is ReminderPhase.DORMANT
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_answered_push_keeps_the_user_active(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[2]
            await make_active(factory, user)
            uid = await user_id_of(factory, user)
            async with factory() as session, session.begin():
                await mark_reminded(session, user_id=uid, local_date=YESTERDAY)
                await session.execute(
                    text(
                        "INSERT INTO praises (user_id, body_ciphertext, iv, local_date) "
                        "VALUES (:uid, :b, :iv, :d)"
                    ),
                    {"uid": uid, "b": b"x", "iv": bytes(12), "d": YESTERDAY},
                )

            sender = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender, sleep=noop_sleep)

            assert (user, REMINDER_NUDGE) in sender.sent  # answered → still nudged
            assert await phase_of(factory, user) is ReminderPhase.ACTIVE
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_dormant_thirty_days_sends_one_return_then_silent(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[3]
            await make_active(factory, user)
            uid = await user_id_of(factory, user)
            long_ago = datetime(2026, 8, 1, 19, 15, tzinfo=UTC)  # 31 days before NOW
            async with factory() as session, session.begin():
                await advance_phase(
                    session,
                    user_id=uid,
                    phase=ReminderPhase.DORMANT,
                    now=long_ago,
                    local_date=date(2026, 8, 1),
                )

            sender = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender, sleep=noop_sleep)
            assert (user, REMINDER_RETURN) in sender.sent
            assert await phase_of(factory, user) is ReminderPhase.SILENT

            # Silent users never get another message.
            sender2 = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender2, sleep=noop_sleep)
            assert all(chat_id != user for chat_id, _ in sender2.sent)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_recently_dormant_user_is_left_quiet(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[4]
            await make_active(factory, user)
            uid = await user_id_of(factory, user)
            recent = datetime(2026, 8, 27, 19, 15, tzinfo=UTC)  # 5 days before NOW
            async with factory() as session, session.begin():
                await advance_phase(
                    session,
                    user_id=uid,
                    phase=ReminderPhase.DORMANT,
                    now=recent,
                    local_date=date(2026, 8, 27),
                )

            sender = FakeSender()
            await deliver_reminders(factory, NOW, sender=sender, sleep=noop_sleep)

            assert all(chat_id != user for chat_id, _ in sender.sent)
            assert await phase_of(factory, user) is ReminderPhase.DORMANT
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_throttled_send_leaves_state_for_retry(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[5]
            await make_active(factory, user)
            sender = ThrottlingSender()
            slept: list[float] = []

            async def sleep(seconds: float) -> None:
                slept.append(seconds)

            await deliver_reminders(factory, NOW, sender=sender, sleep=sleep)

            assert sender.calls == 3  # exhausted the attempt budget
            assert len(slept) == 2
            # State untouched, so the next cycle retries this user.
            async with factory() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT last_reminded_on FROM reminder_states rs "
                            "JOIN users u ON u.id = rs.user_id WHERE u.telegram_id = :t"
                        ),
                        {"t": user},
                    )
                ).scalar_one()
            assert row is None
            assert await phase_of(factory, user) is ReminderPhase.ACTIVE
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_writing_a_praise_reactivates_a_faded_reminder(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[6]
            await make_active(factory, user)
            uid = await user_id_of(factory, user)
            async with factory() as session, session.begin():
                await advance_phase(
                    session,
                    user_id=uid,
                    phase=ReminderPhase.SILENT,
                    now=datetime(2026, 7, 1, 19, 15, tzinfo=UTC),
                    local_date=date(2026, 7, 1),
                )

            async with factory() as session:
                await create_praise(
                    session,
                    telegram_id=user,
                    ciphertext=b"re-engaged",
                    iv=bytes(12),
                    now=lambda: NOW,
                )

            settings = None
            async with factory() as session:
                settings = await get_settings(session, telegram_id=user)
            assert settings.phase is ReminderPhase.ACTIVE
            assert settings.dm_available is True
        finally:
            await engine.dispose()

    asyncio.run(scenario())
