import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.praises.repository import get_balance, get_user
from app.modules.praises.service import (
    PraiseNotFound,
    create_praise,
    delete_praise,
    update_praise,
)
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
OWNER = 9_304_001
STRANGER = 9_304_002
MOMENT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


async def delete_test_users(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:ids)"),
                {"ids": [OWNER, STRANGER]},
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


async def read_praise_row(engine, praise_id):
    async with engine.connect() as connection:
        return (
            await connection.execute(
                text(
                    "SELECT body_ciphertext, iv, updated_at, created_at FROM praises WHERE id = :id"
                ),
                {"id": praise_id},
            )
        ).one_or_none()


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_edit_changes_fields_without_awarding_or_revoking_a_star(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=OWNER, timezone="UTC")
            async with factory() as session:
                await open_session(session, telegram_id=STRANGER, timezone="UTC")

            async with factory() as session:
                created = await create_praise(
                    session,
                    telegram_id=OWNER,
                    ciphertext=b"original",
                    iv=bytes(12),
                    now=lambda: MOMENT,
                )
            assert created.star_awarded is True

            before = await read_praise_row(engine, created.id)

            async with factory() as session:
                await update_praise(
                    session,
                    telegram_id=OWNER,
                    praise_id=created.id,
                    ciphertext=b"edited-body",
                    iv=bytes([1] * 12),
                )

            after = await read_praise_row(engine, created.id)
            assert bytes(after.body_ciphertext) == b"edited-body"
            assert after.updated_at >= before.updated_at
            assert after.created_at == before.created_at

            async with factory() as session:
                owner = await get_user(session, telegram_id=OWNER)
                assert await get_balance(session, user_id=owner.id) == 1

            # A stranger cannot edit someone else's praise.
            with pytest.raises(PraiseNotFound):
                async with factory() as session:
                    await update_praise(
                        session,
                        telegram_id=STRANGER,
                        praise_id=created.id,
                        ciphertext=b"hijack",
                        iv=bytes(12),
                    )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_delete_removes_only_own_praise_and_keeps_the_star(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                await open_session(session, telegram_id=OWNER, timezone="UTC")
            async with factory() as session:
                await open_session(session, telegram_id=STRANGER, timezone="UTC")

            async with factory() as session:
                created = await create_praise(
                    session,
                    telegram_id=OWNER,
                    ciphertext=b"to-delete",
                    iv=bytes(12),
                    now=lambda: MOMENT,
                )

            # A stranger cannot delete it.
            with pytest.raises(PraiseNotFound):
                async with factory() as session:
                    await delete_praise(session, telegram_id=STRANGER, praise_id=created.id)

            # A random id also 404s for the owner.
            with pytest.raises(PraiseNotFound):
                async with factory() as session:
                    await delete_praise(session, telegram_id=OWNER, praise_id=uuid4())

            async with factory() as session:
                await delete_praise(session, telegram_id=OWNER, praise_id=created.id)

            assert await read_praise_row(engine, created.id) is None

            async with factory() as session:
                owner = await get_user(session, telegram_id=OWNER)
                # The daily star is NOT revoked when the praise is deleted.
                assert await get_balance(session, user_id=owner.id) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())
