import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.praises.service import create_praise
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TELEGRAM_IDS = (9_204_001, 9_204_002)
FIXED_MOMENT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


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


async def count_praises(database_url: str, user_telegram_id: int) -> int:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return (
                await connection.execute(
                    text(
                        "SELECT count(*) FROM praises p JOIN users u ON u.id = p.user_id "
                        "WHERE u.telegram_id = :tid"
                    ),
                    {"tid": user_telegram_id},
                )
            ).scalar_one()
    finally:
        await engine.dispose()


async def seed_user(session_factory: async_sessionmaker, telegram_id: int) -> None:
    async with session_factory() as session:
        await open_session(session, telegram_id=telegram_id, timezone="Europe/Moscow")


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
def test_first_praise_earns_one_star_and_second_does_not(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_user(session_factory, TELEGRAM_IDS[0])

            async with session_factory() as session:
                first = await create_praise(
                    session,
                    telegram_id=TELEGRAM_IDS[0],
                    ciphertext=b"blob-1",
                    iv=bytes(12),
                    now=lambda: FIXED_MOMENT,
                )
            async with session_factory() as session:
                second = await create_praise(
                    session,
                    telegram_id=TELEGRAM_IDS[0],
                    ciphertext=b"blob-2",
                    iv=bytes(12),
                    now=lambda: FIXED_MOMENT,
                )

            assert first.star_awarded is True
            assert first.balance == 1
            assert second.star_awarded is False
            assert second.balance == 1
            assert await count_praises(database_url, TELEGRAM_IDS[0]) == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_concurrent_first_praises_award_exactly_one_star(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_user(session_factory, TELEGRAM_IDS[1])

            async def once(blob: bytes) -> bool:
                async with session_factory() as session:
                    result = await create_praise(
                        session,
                        telegram_id=TELEGRAM_IDS[1],
                        ciphertext=blob,
                        iv=bytes(12),
                        now=lambda: FIXED_MOMENT,
                    )
                    return result.star_awarded

            awarded = await asyncio.gather(once(b"a"), once(b"b"))

            assert sum(1 for granted in awarded if granted) == 1
            assert await count_praises(database_url, TELEGRAM_IDS[1]) == 2
        finally:
            await engine.dispose()

    asyncio.run(scenario())
