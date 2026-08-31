import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Date, LargeBinary, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


async def assert_praises_schema_contract(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            columns = await connection.run_sync(
                lambda sync: inspect(sync).get_columns("praises")
            )
            by_name = {column["name"]: column for column in columns}
            assert set(by_name) == {
                "id",
                "user_id",
                "body_ciphertext",
                "iv",
                "sticker",
                "local_date",
                "created_at",
                "updated_at",
            }
            assert isinstance(by_name["body_ciphertext"]["type"], LargeBinary)
            assert isinstance(by_name["iv"]["type"], LargeBinary)
            assert isinstance(by_name["local_date"]["type"], Date)
            assert by_name["local_date"]["nullable"] is False

            indexes = await connection.run_sync(
                lambda sync: inspect(sync).get_indexes("praises")
            )
            assert any(index["column_names"] == ["user_id", "local_date"] for index in indexes)

            foreign_keys = await connection.run_sync(
                lambda sync: inspect(sync).get_foreign_keys("praises")
            )
            assert foreign_keys[0]["referred_table"] == "users"
    finally:
        await engine.dispose()


async def assert_praises_table_absent(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            has_table = await connection.run_sync(
                lambda sync: inspect(sync).has_table("praises")
            )
            assert has_table is False
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not RUN_DATABASE_TESTS,
    reason="set RUN_DATABASE_TESTS=1 with an isolated PostgreSQL database",
)
def test_clean_database_upgrades_to_praises_schema() -> None:
    database_url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.downgrade(config, "base")
    try:
        command.upgrade(config, "head")
        asyncio.run(assert_praises_schema_contract(database_url))

        command.downgrade(config, "20260831_0001")
        asyncio.run(assert_praises_table_absent(database_url))
    finally:
        command.upgrade(config, "head")
