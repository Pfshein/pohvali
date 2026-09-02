"""Database role contract tests (run with an isolated PostgreSQL instance)."""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.users.models import User, UserRole
from app.modules.users.service import UserNotFound, is_admin_user, open_session, set_user_role
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


@pytest_asyncio.fixture
async def database_session() -> AsyncIterator[AsyncSession]:
    if not RUN_DATABASE_TESTS:
        pytest.skip("requires isolated PostgreSQL")
    database_url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    await asyncio.to_thread(command.upgrade, config, "head")
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            async with session.begin():
                await session.execute(
                    delete(User).where(User.telegram_id.in_([8_801_001, 8_801_002]))
                )
    await engine.dispose()


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
@pytest.mark.asyncio
async def test_role_transitions_are_idempotent_and_unknown_does_not_create_rows(
    database_session,
):
    telegram_id = 8_801_001
    user = await open_session(database_session, telegram_id=telegram_id, timezone="UTC")
    assert user.role == UserRole.USER.value

    changed = await set_user_role(
        database_session, telegram_id=telegram_id, role=UserRole.ADMIN
    )
    assert changed.role == UserRole.ADMIN.value
    assert await is_admin_user(database_session, telegram_id=telegram_id)

    reopened = await open_session(
        database_session,
        telegram_id=telegram_id,
        timezone="Europe/Moscow",
    )
    assert reopened.role == UserRole.ADMIN.value
    assert reopened.timezone == "Europe/Moscow"

    repeated = await set_user_role(
        database_session, telegram_id=telegram_id, role=UserRole.ADMIN
    )
    assert repeated.id == user.id

    await set_user_role(database_session, telegram_id=telegram_id, role=UserRole.USER)
    assert not await is_admin_user(database_session, telegram_id=telegram_id)
    with pytest.raises(UserNotFound):
        await set_user_role(
            database_session, telegram_id=8_801_002, role=UserRole.ADMIN
        )
