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

from app.modules.praises.service import create_praise, list_day_praises
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
OWNER = 9_206_001
STRANGER = 9_206_002
DAY_ONE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
DAY_TWO = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


async def delete_test_users(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:ids)"),
                {"ids": [OWNER, STRANGER]},
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    asyncio.run(delete_test_users(url))
    yield url
    asyncio.run(delete_test_users(url))


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_day_read_returns_only_owner_entries_for_that_day(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=OWNER, timezone="UTC")
            async with factory() as session:
                await open_session(session, telegram_id=STRANGER, timezone="UTC")

            async def add(tid: int, blob: bytes, moment: datetime) -> None:
                async with factory() as session:
                    await create_praise(
                        session,
                        telegram_id=tid,
                        ciphertext=blob,
                        iv=bytes(12),
                        now=lambda: moment,
                    )

            await add(OWNER, b"owner-day1-a", DAY_ONE)
            await add(OWNER, b"owner-day1-b", DAY_ONE)
            await add(OWNER, b"owner-day2", DAY_TWO)
            await add(STRANGER, b"stranger-day1", DAY_ONE)

            async with factory() as session:
                day_one = await list_day_praises(
                    session, telegram_id=OWNER, day=date(2026, 9, 1)
                )

            assert len(day_one) == 2
            assert {bytes(p.body_ciphertext) for p in day_one} == {
                b"owner-day1-a",
                b"owner-day1-b",
            }
        finally:
            await engine.dispose()

    asyncio.run(scenario())
