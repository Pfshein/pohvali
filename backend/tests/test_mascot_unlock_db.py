import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.mascots.repository import unlock_eligible_mascots
from app.modules.praises.repository import get_user
from app.modules.praises.service import create_praise
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TELEGRAM_IDS = (9_402_001, 9_402_002)
TENTH_DAY = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


async def delete_test_users(database_url: str) -> None:
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
    asyncio.run(delete_test_users(url))
    yield url
    asyncio.run(delete_test_users(url))


async def seed_daily_stars(
    session_factory: async_sessionmaker, telegram_id: int, count: int
) -> None:
    async with session_factory() as session:
        await open_session(session, telegram_id=telegram_id, timezone="UTC")
    async with session_factory() as session, session.begin():
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        start = date(2026, 1, 1)
        for offset in range(count):
            await session.execute(
                text(
                    "INSERT INTO star_ledger (user_id, amount, reason, local_date) "
                    "VALUES (:uid, 1, 'daily', :day)"
                ),
                {"uid": user.id, "day": start + timedelta(days=offset)},
            )
        await session.execute(
            text("INSERT INTO star_balances (user_id, balance) VALUES (:uid, :balance)"),
            {"uid": user.id, "balance": count},
        )


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_tenth_daily_star_unlocks_tisha_once_in_create_transaction(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_daily_stars(session_factory, TELEGRAM_IDS[0], 9)

            async with session_factory() as session:
                tenth = await create_praise(
                    session,
                    telegram_id=TELEGRAM_IDS[0],
                    ciphertext=b"tenth",
                    iv=bytes(12),
                    now=lambda: TENTH_DAY,
                )
            async with session_factory() as session:
                repeated = await create_praise(
                    session,
                    telegram_id=TELEGRAM_IDS[0],
                    ciphertext=b"same-day",
                    iv=bytes(12),
                    now=lambda: TENTH_DAY,
                )

            assert tenth.newly_unlocked == ("tisha",)
            assert repeated.newly_unlocked == ()

            async with engine.connect() as connection:
                rows = (
                    await connection.execute(
                        text(
                            "SELECT mascot_code, threshold FROM mascot_unlocks mu "
                            "JOIN users u ON u.id = mu.user_id WHERE u.telegram_id = :tid"
                        ),
                        {"tid": TELEGRAM_IDS[0]},
                    )
                ).all()
            assert rows == [("tisha", 10)]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_hundred_stars_backfills_all_thresholds_idempotently(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_daily_stars(session_factory, TELEGRAM_IDS[1], 100)
            async with session_factory() as session, session.begin():
                user = await get_user(session, telegram_id=TELEGRAM_IDS[1])
                assert user is not None
                first = await unlock_eligible_mascots(
                    session,
                    user_id=user.id,
                    earned_stars=100,
                )
                second = await unlock_eligible_mascots(
                    session,
                    user_id=user.id,
                    earned_stars=100,
                )

            assert first == ["tisha", "lumi", "bim"]
            assert second == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_unlock_migration_schema(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                mascot_columns = await connection.run_sync(
                    lambda sync: {column["name"] for column in inspect(sync).get_columns("mascots")}
                )
                unlock_columns = await connection.run_sync(
                    lambda sync: {
                        column["name"] for column in inspect(sync).get_columns("mascot_unlocks")
                    }
                )
            assert "unlock_threshold" in mascot_columns
            assert unlock_columns == {"user_id", "mascot_code", "threshold", "unlocked_at"}
        finally:
            await engine.dispose()

    asyncio.run(scenario())
