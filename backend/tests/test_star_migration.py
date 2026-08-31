import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


async def assert_star_schema_contract(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            ledger_columns = await connection.run_sync(
                lambda sync: {c["name"] for c in inspect(sync).get_columns("star_ledger")}
            )
            assert ledger_columns == {
                "id",
                "user_id",
                "amount",
                "reason",
                "local_date",
                "created_at",
            }

            indexes = await connection.run_sync(
                lambda sync: inspect(sync).get_indexes("star_ledger")
            )
            daily = next(i for i in indexes if i["name"] == "uq_star_ledger_daily_per_day")
            assert daily["unique"] is True
            assert daily["column_names"] == ["user_id", "local_date"]

            balance_columns = await connection.run_sync(
                lambda sync: {c["name"] for c in inspect(sync).get_columns("star_balances")}
            )
            assert balance_columns == {"user_id", "balance", "updated_at"}

        # A user seeded once, then two daily entries for the same day must collide.
        async with engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO users (telegram_id) VALUES (:tid)"), {"tid": 9_401_001}
            )
            user_id = (
                await connection.execute(
                    text("SELECT id FROM users WHERE telegram_id = :tid"), {"tid": 9_401_001}
                )
            ).scalar_one()
            await connection.execute(
                text(
                    "INSERT INTO star_ledger (user_id, amount, reason, local_date) "
                    "VALUES (:uid, 1, 'daily', DATE '2026-09-01')"
                ),
                {"uid": user_id},
            )

        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO star_ledger (user_id, amount, reason, local_date) "
                        "VALUES (:uid, 1, 'daily', DATE '2026-09-01')"
                    ),
                    {"uid": user_id},
                )

        # Balance CHECK forbids negatives.
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    text("INSERT INTO star_balances (user_id, balance) VALUES (:uid, -1)"),
                    {"uid": user_id},
                )
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not RUN_DATABASE_TESTS,
    reason="set RUN_DATABASE_TESTS=1 with an isolated PostgreSQL database",
)
def test_clean_database_upgrades_to_star_schema() -> None:
    database_url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.downgrade(config, "base")
    try:
        command.upgrade(config, "head")
        asyncio.run(assert_star_schema_contract(database_url))
    finally:
        command.downgrade(config, "base")
        command.upgrade(config, "head")
