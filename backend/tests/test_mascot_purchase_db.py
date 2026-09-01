import asyncio
import os
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.mascots.repository import get_user
from app.modules.mascots.seed import seed_mascot_catalog
from app.modules.mascots.service import (
    InsufficientStars,
    MascotLocked,
    MascotState,
    NotOwned,
    list_collection,
    purchase_mascot,
    set_active_mascot,
)
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
TELEGRAM_IDS = (9_403_001, 9_403_002, 9_403_003, 9_403_004, 9_403_005)


async def reset_state(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:ids)"),
                {"ids": list(TELEGRAM_IDS)},
            )
        async with async_sessionmaker(engine, expire_on_commit=False)() as session, session.begin():
            await seed_mascot_catalog(session)
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    asyncio.run(reset_state(url))
    yield url
    asyncio.run(reset_state(url))


async def seed_stars(
    session_factory: async_sessionmaker,
    telegram_id: int,
    *,
    earned: int,
    balance: int,
) -> None:
    async with session_factory() as session:
        await open_session(session, telegram_id=telegram_id, timezone="UTC")
    async with session_factory() as session, session.begin():
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        start = date(2026, 1, 1)
        for offset in range(earned):
            await session.execute(
                text(
                    "INSERT INTO star_ledger (user_id, amount, reason, local_date) "
                    "VALUES (:uid, 1, 'daily', :day)"
                ),
                {"uid": user.id, "day": start + timedelta(days=offset)},
            )
        await session.execute(
            text("INSERT INTO star_balances (user_id, balance) VALUES (:uid, :balance)"),
            {"uid": user.id, "balance": balance},
        )


async def read_balance(session_factory: async_sessionmaker, telegram_id: int) -> int:
    async with session_factory() as session:
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        result = await session.execute(
            text("SELECT balance FROM star_balances WHERE user_id = :uid"),
            {"uid": user.id},
        )
        return result.scalar_one()


async def read_ownership(session_factory: async_sessionmaker, telegram_id: int) -> list[tuple]:
    async with session_factory() as session:
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        result = await session.execute(
            text(
                "SELECT mascot_code, price_paid FROM mascot_ownership "
                "WHERE user_id = :uid ORDER BY mascot_code"
            ),
            {"uid": user.id},
        )
        return [(row.mascot_code, row.price_paid) for row in result.all()]


async def read_purchase_ledger(session_factory: async_sessionmaker, telegram_id: int) -> list[int]:
    async with session_factory() as session:
        user = await get_user(session, telegram_id=telegram_id)
        assert user is not None
        result = await session.execute(
            text(
                "SELECT amount FROM star_ledger WHERE user_id = :uid AND reason = 'purchase' "
                "ORDER BY created_at"
            ),
            {"uid": user.id},
        )
        return [row.amount for row in result.all()]


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_purchase_debits_once_and_is_idempotent(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_stars(factory, TELEGRAM_IDS[0], earned=10, balance=10)

            async with factory() as session:
                first = await purchase_mascot(
                    session, telegram_id=TELEGRAM_IDS[0], code="tisha"
                )
            async with factory() as session:
                second = await purchase_mascot(
                    session, telegram_id=TELEGRAM_IDS[0], code="tisha"
                )

            assert first.newly_purchased is True
            assert first.balance == 0
            assert second.newly_purchased is False
            assert second.balance == 0

            assert await read_balance(factory, TELEGRAM_IDS[0]) == 0
            assert await read_ownership(factory, TELEGRAM_IDS[0]) == [("tisha", 10)]
            assert await read_purchase_ledger(factory, TELEGRAM_IDS[0]) == [-10]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_locked_mascot_cannot_be_purchased(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_stars(factory, TELEGRAM_IDS[1], earned=9, balance=9)

            async with factory() as session:
                with pytest.raises(MascotLocked):
                    await purchase_mascot(session, telegram_id=TELEGRAM_IDS[1], code="tisha")

            assert await read_balance(factory, TELEGRAM_IDS[1]) == 9
            assert await read_ownership(factory, TELEGRAM_IDS[1]) == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_insufficient_stars_does_not_debit(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            # Earned 30 (lumi unlocked) but only 5 spendable stars left.
            await seed_stars(factory, TELEGRAM_IDS[2], earned=30, balance=5)

            async with factory() as session:
                with pytest.raises(InsufficientStars):
                    await purchase_mascot(session, telegram_id=TELEGRAM_IDS[2], code="lumi")

            assert await read_balance(factory, TELEGRAM_IDS[2]) == 5
            assert await read_ownership(factory, TELEGRAM_IDS[2]) == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_concurrent_purchases_never_double_spend(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            # Enough to unlock both tisha (10) and lumi (30), but only 30 stars to spend.
            # Buying both would cost 40 — the row lock must prevent overspending.
            await seed_stars(factory, TELEGRAM_IDS[3], earned=30, balance=30)

            async def buy(code: str) -> object:
                async with factory() as session:
                    return await purchase_mascot(
                        session, telegram_id=TELEGRAM_IDS[3], code=code
                    )

            results = await asyncio.gather(
                buy("tisha"), buy("lumi"), return_exceptions=True
            )

            succeeded = [r for r in results if not isinstance(r, Exception)]
            insufficient = [r for r in results if isinstance(r, InsufficientStars)]
            assert len(succeeded) == 1
            assert len(insufficient) == 1

            ownership = await read_ownership(factory, TELEGRAM_IDS[3])
            assert len(ownership) == 1
            (_, price_paid) = ownership[0]
            balance = await read_balance(factory, TELEGRAM_IDS[3])
            assert balance == 30 - price_paid
            assert balance >= 0
            assert await read_purchase_ledger(factory, TELEGRAM_IDS[3]) == [-price_paid]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_activate_requires_ownership_and_catalog_states(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            await seed_stars(factory, TELEGRAM_IDS[4], earned=10, balance=10)

            # A free starter can be activated without ownership rows.
            async with factory() as session:
                await set_active_mascot(session, telegram_id=TELEGRAM_IDS[4], code="ava")

            # A locked, unowned mascot cannot be activated.
            async with factory() as session:
                with pytest.raises(NotOwned):
                    await set_active_mascot(session, telegram_id=TELEGRAM_IDS[4], code="bim")

            # Purchase then activate the owned mascot.
            async with factory() as session:
                await purchase_mascot(session, telegram_id=TELEGRAM_IDS[4], code="tisha")
            async with factory() as session:
                await set_active_mascot(session, telegram_id=TELEGRAM_IDS[4], code="tisha")

            async with factory() as session:
                collection = await list_collection(session, telegram_id=TELEGRAM_IDS[4])

            states = {item.code: item.state for item in collection.mascots}
            active = {item.code for item in collection.mascots if item.active}
            assert collection.active_mascot == "tisha"
            assert active == {"tisha"}
            assert states["ava"] == MascotState.OWNED  # starter, free
            assert states["tisha"] == MascotState.OWNED  # purchased
            assert states["lumi"] == MascotState.LOCKED  # earned 10 < 30
            assert states["bim"] == MascotState.LOCKED  # earned 10 < 100
            assert collection.balance == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_ownership_migration_schema(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                ownership_columns = await connection.run_sync(
                    lambda sync: {
                        column["name"]
                        for column in inspect(sync).get_columns("mascot_ownership")
                    }
                )
                user_columns = await connection.run_sync(
                    lambda sync: {column["name"] for column in inspect(sync).get_columns("users")}
                )
            assert ownership_columns == {
                "user_id",
                "mascot_code",
                "price_paid",
                "acquired_at",
            }
            assert "active_mascot_code" in user_columns
        finally:
            await engine.dispose()

    asyncio.run(scenario())
