import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import BigInteger, DateTime, String, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


async def assert_users_schema_contract(database_url: str) -> None:
    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            columns = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_columns("users")
            )
            column_names = {column["name"] for column in columns}
            assert column_names == {
                "id",
                "telegram_id",
                "timezone",
                "active_mascot_code",
                "created_at",
            }
            columns_by_name = {column["name"]: column for column in columns}

            assert str(columns_by_name["id"]["type"]) == "UUID"
            assert columns_by_name["id"]["nullable"] is False
            assert "gen_random_uuid" in columns_by_name["id"]["default"]

            assert isinstance(columns_by_name["telegram_id"]["type"], BigInteger)
            assert columns_by_name["telegram_id"]["nullable"] is False

            timezone = columns_by_name["timezone"]
            assert isinstance(timezone["type"], String)
            assert timezone["type"].length == 64
            assert timezone["nullable"] is False
            assert "UTC" in timezone["default"]

            created_at = columns_by_name["created_at"]
            assert isinstance(created_at["type"], DateTime)
            assert created_at["type"].timezone is True
            assert created_at["nullable"] is False
            assert "now()" in created_at["default"]

            await connection.execute(
                text("INSERT INTO users (telegram_id) VALUES (:telegram_id)"),
                {"telegram_id": 42},
            )

        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT id, telegram_id, timezone, created_at "
                        "FROM users WHERE telegram_id = :telegram_id"
                    ),
                    {"telegram_id": 42},
                )
            ).one()
            assert row.id is not None
            assert row.telegram_id == 42
            assert row.timezone == "UTC"
            assert row.created_at is not None

            with pytest.raises(IntegrityError):
                await connection.execute(
                    text("INSERT INTO users (telegram_id) VALUES (:telegram_id)"),
                    {"telegram_id": 42},
                )
    finally:
        await engine.dispose()


async def assert_users_table_absent(database_url: str) -> None:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            has_users_table = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).has_table("users")
            )
            assert has_users_table is False
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not RUN_DATABASE_TESTS,
    reason="set RUN_DATABASE_TESTS=1 with an isolated PostgreSQL database",
)
def test_clean_database_upgrades_to_head_with_minimal_user_schema() -> None:
    database_url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.downgrade(config, "base")
    try:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        asyncio.run(assert_users_schema_contract(database_url))

        command.downgrade(config, "base")
        asyncio.run(assert_users_table_absent(database_url))
    finally:
        command.upgrade(config, "head")
