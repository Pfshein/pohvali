import asyncio
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.reminders.service import get_settings, record_dm_available, set_enabled
from app.modules.reminders.state import ReminderPhase
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TELEGRAM_IDS = (9_501_001, 9_501_002, 9_501_003, 9_501_004)


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


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_start_records_dm_availability_creating_the_user(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            # No session opened yet: /start must create the user row.
            async with factory() as session:
                await record_dm_available(session, telegram_id=TELEGRAM_IDS[0])

            async with factory() as session:
                settings = await get_settings(session, telegram_id=TELEGRAM_IDS[0])

            assert settings.dm_available is True
            assert settings.enabled is True
            assert settings.phase is ReminderPhase.ACTIVE
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_defaults_when_no_reminder_row_exists(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=TELEGRAM_IDS[1], timezone="UTC")

            async with factory() as session:
                settings = await get_settings(session, telegram_id=TELEGRAM_IDS[1])

            assert settings.enabled is True
            assert settings.dm_available is False
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_user_can_disable_and_reenable_without_losing_dm_availability(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=TELEGRAM_IDS[2], timezone="UTC")
            async with factory() as session:
                await record_dm_available(session, telegram_id=TELEGRAM_IDS[2])

            async with factory() as session:
                disabled = await set_enabled(
                    session, telegram_id=TELEGRAM_IDS[2], enabled=False
                )
            assert disabled.enabled is False
            assert disabled.dm_available is True  # disabling never clears DM availability

            async with factory() as session:
                enabled = await set_enabled(
                    session, telegram_id=TELEGRAM_IDS[2], enabled=True
                )
            assert enabled.enabled is True
            assert enabled.dm_available is True
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_start_never_overwrites_a_saved_timezone(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(
                    session, telegram_id=TELEGRAM_IDS[3], timezone="Europe/Moscow"
                )
            async with factory() as session:
                await record_dm_available(session, telegram_id=TELEGRAM_IDS[3])

            async with engine.connect() as connection:
                timezone = (
                    await connection.execute(
                        text("SELECT timezone FROM users WHERE telegram_id = :tid"),
                        {"tid": TELEGRAM_IDS[3]},
                    )
                ).scalar_one()
            assert timezone == "Europe/Moscow"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_reminder_states_migration_schema(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                columns = await connection.run_sync(
                    lambda sync: {
                        column["name"]
                        for column in inspect(sync).get_columns("reminder_states")
                    }
                )
            assert columns == {
                "user_id",
                "enabled",
                "dm_available",
                "phase",
                "phase_changed_at",
                "last_reminded_on",
                "updated_at",
            }
        finally:
            await engine.dispose()

    asyncio.run(scenario())
