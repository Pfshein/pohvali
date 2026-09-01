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

from app.modules.reminders.repository import get_user
from app.modules.reminders.scheduler import run_reminder_cycle
from app.modules.reminders.service import (
    mark_reminded,
    record_dm_available,
    select_reminder_candidates,
    set_enabled,
)
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"

# Base ids; each test uses a disjoint slice to stay independent.
TELEGRAM_IDS = tuple(9_502_000 + n for n in range(12))

# Moscow is UTC+3 year-round: 22:15 local == 19:15 UTC.
MSK_2215 = datetime(2026, 9, 1, 19, 15, tzinfo=UTC)
MSK_LOCAL_DATE = date(2026, 9, 1)
MSK_2115 = datetime(2026, 9, 1, 18, 15, tzinfo=UTC)  # 21:15 local — outside window


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


async def make_eligible(factory: async_sessionmaker, telegram_id: int, timezone: str) -> None:
    async with factory() as session:
        await open_session(session, telegram_id=telegram_id, timezone=timezone)
    async with factory() as session:
        await record_dm_available(session, telegram_id=telegram_id)


async def write_praise(factory: async_sessionmaker, telegram_id: int, local_date: date) -> None:
    async with factory() as session, session.begin():
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        await session.execute(
            text(
                "INSERT INTO praises (user_id, body_ciphertext, iv, local_date) "
                "VALUES (:uid, :body, :iv, :day)"
            ),
            {"uid": user.id, "body": b"x", "iv": bytes(12), "day": local_date},
        )


async def candidate_ids(factory: async_sessionmaker, now: datetime) -> set[int]:
    async with factory() as session:
        candidates = await select_reminder_candidates(session, now=now)
    return {candidate.telegram_id for candidate in candidates}


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_selects_only_eligible_users_in_their_local_window(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            eligible = TELEGRAM_IDS[0]
            wrote_today = TELEGRAM_IDS[1]
            disabled = TELEGRAM_IDS[2]
            no_dm = TELEGRAM_IDS[3]
            outside_window = TELEGRAM_IDS[4]

            await make_eligible(factory, eligible, "Europe/Moscow")
            await make_eligible(factory, wrote_today, "Europe/Moscow")
            await write_praise(factory, wrote_today, MSK_LOCAL_DATE)
            await make_eligible(factory, disabled, "Europe/Moscow")
            async with factory() as session:
                await set_enabled(session, telegram_id=disabled, enabled=False)
            async with factory() as session:  # opened a session but never /start
                await open_session(session, telegram_id=no_dm, timezone="Europe/Moscow")
            await make_eligible(factory, outside_window, "Europe/Moscow")

            selected = await candidate_ids(factory, MSK_2215)
            assert eligible in selected
            assert wrote_today not in selected
            assert disabled not in selected
            assert no_dm not in selected

            # At 21:15 local nobody is in the 22:xx window.
            assert outside_window not in await candidate_ids(factory, MSK_2115)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_a_local_day_never_gets_two_pushes(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[5]
            await make_eligible(factory, user, "Europe/Moscow")

            assert user in await candidate_ids(factory, MSK_2215)

            # Once reminded for the local day, later runs in the same hour skip them.
            async with factory() as session:
                fetched = await get_user(session, telegram_id=user)
                assert fetched is not None
                user_id = fetched.id
            async with factory() as session:
                await mark_reminded(session, user_id=user_id, local_date=MSK_LOCAL_DATE)

            later = datetime(2026, 9, 1, 19, 45, tzinfo=UTC)  # 22:45 MSK, same local day
            assert user not in await candidate_ids(factory, later)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_window_follows_the_local_wall_clock_across_dst(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[6]
            await make_eligible(factory, user, "Europe/Berlin")

            # Summer: Berlin is UTC+2, so 20:15 UTC is 22:15 local — in window.
            summer = datetime(2026, 7, 1, 20, 15, tzinfo=UTC)
            assert user in await candidate_ids(factory, summer)

            # Winter: Berlin is UTC+1, so the same 20:15 UTC is 21:15 local — out.
            winter = datetime(2026, 1, 15, 20, 15, tzinfo=UTC)
            assert user not in await candidate_ids(factory, winter)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_run_cycle_delivers_candidates_to_the_handler(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            user = TELEGRAM_IDS[7]
            await make_eligible(factory, user, "Europe/Moscow")

            seen: list[int] = []

            async def handle(candidates) -> None:
                seen.extend(candidate.telegram_id for candidate in candidates)

            await run_reminder_cycle(factory, handle=handle, now=MSK_2215)

            assert user in seen
        finally:
            await engine.dispose()

    asyncio.run(scenario())
