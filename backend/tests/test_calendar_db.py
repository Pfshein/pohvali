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

from app.modules.praises.service import create_praise, list_calendar
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
OWNER = 9_302_001
STRANGER = 9_302_002


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
def test_calendar_collapses_multiple_entries_into_one_marked_day(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=OWNER, timezone="UTC")
            async with factory() as session:
                await open_session(session, telegram_id=STRANGER, timezone="UTC")

            async def add(tid: int, moment: datetime) -> None:
                async with factory() as session:
                    await create_praise(
                        session,
                        telegram_id=tid,
                        ciphertext=b"blob",
                        iv=bytes(12),
                        now=lambda: moment,
                    )

            # Owner: three praises on Sep 1, one on Sep 3.
            for _ in range(3):
                await add(OWNER, datetime(2026, 9, 1, 12, 0, tzinfo=UTC))
            await add(OWNER, datetime(2026, 9, 3, 12, 0, tzinfo=UTC))
            # Stranger writes on Sep 1 too — must not appear for the owner.
            await add(STRANGER, datetime(2026, 9, 1, 12, 0, tzinfo=UTC))

            async with factory() as session:
                days = await list_calendar(
                    session,
                    telegram_id=OWNER,
                    start=date(2026, 9, 1),
                    end=date(2026, 9, 30),
                )

            assert days == [(date(2026, 9, 1), 3), (date(2026, 9, 3), 1)]
        finally:
            await engine.dispose()

    asyncio.run(scenario())
