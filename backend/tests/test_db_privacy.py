import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db import create_database_engine
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


async def render_database_error(database_url: str, sensitive_value: int) -> str:
    engine = create_database_engine(database_url)
    session_factory = async_sessionmaker(engine)
    try:
        async with session_factory() as session:
            with pytest.raises(DBAPIError) as caught:
                await session.execute(
                    text("SELECT CAST(:telegram_id AS BIGINT) / 0"),
                    {"telegram_id": sensitive_value},
                )
            return str(caught.value)
    finally:
        await engine.dispose()


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_database_errors_hide_bound_parameters() -> None:
    database_url = require_test_database_url(os.environ)
    sensitive_telegram_id = 8_900_123_456

    rendered_error = asyncio.run(
        render_database_error(database_url, sensitive_telegram_id)
    )

    assert str(sensitive_telegram_id) not in rendered_error
    assert "SQL parameters hidden" in rendered_error
