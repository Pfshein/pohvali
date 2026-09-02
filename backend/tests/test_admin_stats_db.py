"""PostgreSQL contracts for PH-802.

These tests intentionally skip unless an isolated ``*_test`` PostgreSQL URL is
provided, matching the repository's existing database-test convention.
"""

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.users.service import erase_account, open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TEST_TELEGRAM_IDS = tuple(9_802_000 + index for index in range(1, 11))
FIXED_NOW = datetime(2099, 4, 20, 12, 0, tzinfo=UTC)


def _config(database_url: str) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


async def _cleanup(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:ids)"),
                {"ids": list(TEST_TELEGRAM_IDS)},
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database_url():
    url = require_test_database_url(os.environ)
    command.upgrade(_config(url), "head")
    asyncio.run(_cleanup(url))
    yield url
    asyncio.run(_cleanup(url))


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_activity_migration_schema_contract(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                columns = await connection.run_sync(
                    lambda sync: {
                        item["name"]: item
                        for item in inspect(sync).get_columns("user_activity_days")
                    }
                )
                assert set(columns) == {
                    "user_id",
                    "activity_date",
                    "first_opened_at",
                    "last_opened_at",
                    "open_count",
                }
                indexes = await connection.run_sync(
                    lambda sync: inspect(sync).get_indexes("user_activity_days")
                )
                assert any(index["column_names"] == ["activity_date"] for index in indexes)
                constraints = await connection.execute(
                    text(
                        "SELECT constraint_name FROM information_schema.check_constraints "
                        "WHERE constraint_name = 'ck_user_activity_days_open_count_positive'"
                    )
                )
                assert constraints.scalar_one_or_none() is not None
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_backfill_aggregates_multiple_praises_on_one_utc_day(database_url: str) -> None:
    async def seed_revision_0011() -> tuple[object, object]:
        account_opened = datetime(2026, 1, 3, 22, 0, tzinfo=UTC)
        first_praise = datetime(2026, 1, 3, 23, 30, tzinfo=UTC)
        second_praise = datetime(2026, 1, 3, 23, 45, tzinfo=UTC)
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as connection:
                user_id = (
                    await connection.execute(
                        text(
                            "INSERT INTO users (telegram_id, timezone, created_at) "
                            "VALUES (:telegram_id, 'UTC', :created_at) RETURNING id"
                        ),
                        {
                            "telegram_id": TEST_TELEGRAM_IDS[0],
                            "created_at": account_opened,
                        },
                    )
                ).scalar_one()
                user_without_praise = (
                    await connection.execute(
                        text(
                            "INSERT INTO users (telegram_id, timezone, created_at) "
                            "VALUES (:telegram_id, 'UTC', :created_at) RETURNING id"
                        ),
                        {
                            "telegram_id": TEST_TELEGRAM_IDS[6],
                            "created_at": account_opened,
                        },
                    )
                ).scalar_one()
                for moment in (first_praise, second_praise):
                    await connection.execute(
                        text(
                            "INSERT INTO praises "
                            "(id, user_id, body_ciphertext, iv, local_date, created_at, "
                            "updated_at) VALUES (:id, :user_id, :body, :iv, :local_date, "
                            ":created_at, :updated_at)"
                        ),
                        {
                            "id": uuid4(),
                            "user_id": user_id,
                            "body": b"opaque",
                            "iv": bytes(12),
                            "local_date": date(2026, 1, 3),
                            "created_at": moment,
                            "updated_at": moment,
                        },
                    )
                return user_id, user_without_praise
        finally:
            await engine.dispose()

    async def assert_backfill(user_id: object, user_without_praise: object) -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                rows = (
                    await connection.execute(
                        text(
                            "SELECT activity_date, open_count, first_opened_at, last_opened_at "
                            "FROM user_activity_days WHERE user_id = :user_id"
                        ),
                        {"user_id": user_id},
                    )
                ).all()
                assert len(rows) == 1
                assert rows[0].activity_date == date(2026, 1, 3)
                assert rows[0].open_count == 1
                assert rows[0].first_opened_at == datetime(
                    2026, 1, 3, 22, 0, tzinfo=UTC
                )
                assert rows[0].last_opened_at == datetime(
                    2026, 1, 3, 23, 45, tzinfo=UTC
                )
                no_praise_rows = (
                    await connection.execute(
                        text(
                            "SELECT activity_date, open_count FROM user_activity_days "
                            "WHERE user_id = :user_id"
                        ),
                        {"user_id": user_without_praise},
                    )
                ).all()
                assert [(row.activity_date, row.open_count) for row in no_praise_rows] == [
                    (date(2026, 1, 3), 1)
                ]
        finally:
            await engine.dispose()

    command.downgrade(_config(database_url), "20260902_0011")
    try:
        user_id, user_without_praise = asyncio.run(seed_revision_0011())
        command.upgrade(_config(database_url), "head")
        asyncio.run(assert_backfill(user_id, user_without_praise))
    finally:
        command.upgrade(_config(database_url), "head")


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_activity_upsert_is_utc_dated_monotonic_and_concurrent(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            observed = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)

            async with factory() as session:
                await session.execute(
                    text(
                        "INSERT INTO users (telegram_id, timezone) VALUES (:id, 'UTC')"
                    ),
                    {"id": TEST_TELEGRAM_IDS[1]},
                )
                await session.commit()

            async def once(moment: datetime) -> None:
                async with factory() as session:
                    await open_session(
                        session,
                        telegram_id=TEST_TELEGRAM_IDS[1],
                        timezone="UTC",
                        observed_at=moment,
                    )

            await once(observed)
            await once(observed - timedelta(hours=1))
            await asyncio.gather(*(once(observed) for _ in range(2)))
            async with factory() as session:
                rows = (
                    await session.execute(
                        text(
                            "SELECT activity_date, open_count, first_opened_at, last_opened_at "
                            "FROM user_activity_days d JOIN users u ON u.id = d.user_id "
                            "WHERE u.telegram_id = :id ORDER BY activity_date"
                        ),
                        {"id": TEST_TELEGRAM_IDS[1]},
                    )
                ).all()
            assert len(rows) == 1
            assert rows[0].activity_date == date(2026, 2, 1)
            assert rows[0].open_count == 4
            assert rows[0].first_opened_at == observed
            assert rows[0].last_opened_at == observed

            next_day = observed + timedelta(days=1, hours=2)
            await once(next_day)
            async with factory() as session:
                count = (
                    await session.execute(
                        text(
                            "SELECT count(*) FROM user_activity_days d "
                            "JOIN users u ON u.id = d.user_id WHERE u.telegram_id = :id"
                        ),
                        {"id": TEST_TELEGRAM_IDS[1]},
                    )
                ).scalar_one()
            assert count == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_period_aggregates_use_today_7_and_30_day_utc_boundaries(
    database_url: str,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as connection:
                users = []
                for offset in range(2, 6):
                    users.append(
                        (
                            await connection.execute(
                                text(
                                    "INSERT INTO users (telegram_id, timezone) "
                                    "VALUES (:id, 'UTC') RETURNING id"
                                ),
                                {"id": TEST_TELEGRAM_IDS[offset]},
                            )
                        ).scalar_one()
                    )
                moments = (
                    FIXED_NOW,
                    datetime(2099, 4, 14, 0, 0, tzinfo=UTC),
                    datetime(2099, 3, 22, 0, 0, tzinfo=UTC),
                    datetime(2099, 3, 21, 23, 59, 59, tzinfo=UTC),
                )
                for user_id, moment in zip(users, moments, strict=True):
                    await connection.execute(
                        text(
                            "INSERT INTO user_activity_days "
                            "(user_id, activity_date, first_opened_at, last_opened_at, open_count) "
                            "VALUES (:user_id, :day, :moment, :moment, 1)"
                        ),
                        {
                            "user_id": user_id,
                            "day": moment.date(),
                            "moment": moment,
                        },
                    )
                for user_id, moment in zip(users, moments, strict=True):
                    await connection.execute(
                        text(
                            "INSERT INTO praises "
                            "(id, user_id, body_ciphertext, iv, local_date, created_at, "
                            "updated_at) VALUES (:id, :user_id, :body, :iv, :local_date, "
                            ":created_at, :updated_at)"
                        ),
                        {
                            "id": uuid4(),
                            "user_id": user_id,
                            "body": b"opaque",
                            "iv": bytes(12),
                            "local_date": moment.date(),
                            "created_at": moment,
                            "updated_at": moment,
                        },
                    )
                # Exactly at the exclusive upper boundary: never counted in
                # today/7/30 despite belonging to a known user.
                next_day = datetime(2099, 4, 21, 0, 0, tzinfo=UTC)
                await connection.execute(
                    text(
                        "INSERT INTO praises "
                        "(id, user_id, body_ciphertext, iv, local_date, created_at, "
                        "updated_at) VALUES (:id, :user_id, :body, :iv, :local_date, "
                        ":created_at, :updated_at)"
                    ),
                    {
                        "id": uuid4(),
                        "user_id": users[0],
                        "body": b"opaque",
                        "iv": bytes(12),
                        "local_date": next_day.date(),
                        "created_at": next_day,
                        "updated_at": next_day,
                    },
                )

            from app.modules.admin_stats.service import PeriodStats, get_stats_snapshot

            factory = async_sessionmaker(engine, expire_on_commit=False)
            async with factory() as session:
                snapshot = await get_stats_snapshot(session, now=FIXED_NOW)
            assert snapshot.today == PeriodStats(1, 1, 1)
            assert snapshot.last_7_days == PeriodStats(2, 2, 2)
            assert snapshot.last_30_days == PeriodStats(3, 3, 3)
            assert snapshot.all_time.opened_users >= 4
            assert snapshot.all_time.praised_users >= 4
            assert snapshot.all_time.praises >= 5
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_account_deletion_cascades_activity(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(
                    session,
                    telegram_id=TEST_TELEGRAM_IDS[5],
                    timezone="UTC",
                    observed_at=FIXED_NOW,
                )
                user_id = await session.scalar(
                    text("SELECT id FROM users WHERE telegram_id = :id"),
                    {"id": TEST_TELEGRAM_IDS[5]},
                )
                await session.execute(
                    text(
                        "INSERT INTO user_activity_days "
                        "(user_id, activity_date, first_opened_at, last_opened_at, open_count) "
                        "SELECT id, :day, :moment, :moment, 1 FROM users WHERE telegram_id = :id"
                    ),
                    {
                        "id": TEST_TELEGRAM_IDS[5],
                        "day": date(2099, 4, 21),
                        "moment": FIXED_NOW,
                    },
                )
                await session.commit()
            async with factory() as session:
                await erase_account(session, telegram_id=TEST_TELEGRAM_IDS[5])
                remaining = await session.scalar(
                    text(
                        "SELECT count(*) FROM user_activity_days WHERE user_id = :user_id"
                    ),
                    {"user_id": user_id},
                )
            assert remaining == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())
