import asyncio
import os
import struct
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.dependencies import get_db_session
from app.main import app
from app.modules.mascots.service import (
    MascotCodeTaken,
    ThresholdTaken,
    add_mascot,
)
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"

TEST_CODE = "test_umka"
TEST_CODE_2 = "test_tish2"


def build_png(*, width: int = 512, height: int = 512) -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + chunk_type + payload + b"\x00\x00\x00\x00"

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


async def read_mascot(database_url: str, code: str) -> dict | None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT code, name, blurb, asset_path, starter, active, "
                        "unlock_threshold, sort_order, image_data "
                        "FROM mascots WHERE code = :code"
                    ),
                    {"code": code},
                )
            ).mappings().first()
            return dict(row) if row is not None else None
    finally:
        await engine.dispose()


async def delete_test_mascots(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM mascots WHERE code = ANY(:codes)"),
                {"codes": [TEST_CODE, TEST_CODE_2]},
            )
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    asyncio.run(delete_test_mascots(url))
    yield url
    asyncio.run(delete_test_mascots(url))


@pytest.fixture(scope="module")
def client(database_url: str) -> Iterator[TestClient]:
    # Override the session dependency instead of the global settings: the app's
    # engine is process-wide cached, and binding it to this module's event loop
    # would poison later modules that use TestClient with their own loop.
    async def override_db_session() -> AsyncIterator[object]:
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                yield session
        finally:
            await engine.dispose()

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


async def count_mascots(database_url: str, code: str) -> int:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return int(
                (
                    await connection.execute(
                        text("SELECT count(*) FROM mascots WHERE code = :code"),
                        {"code": code},
                    )
                ).scalar_one()
            )
    finally:
        await engine.dispose()


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_add_mascot_creates_catalog_entry_with_image(database_url: str) -> None:
    image = build_png()

    async def run() -> bool:
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await add_mascot(
                    session,
                    code=TEST_CODE,
                    name="Умка",
                    blurb="Тихий и загадочный",
                    unlock_threshold=411,
                    image_data=image,
                )
        finally:
            await engine.dispose()

    assert asyncio.run(run()) is True

    row = asyncio.run(read_mascot(database_url, TEST_CODE))
    assert row is not None
    assert row["name"] == "Умка"
    assert row["blurb"] == "Тихий и загадочный"
    assert row["unlock_threshold"] == 411
    assert row["starter"] is False
    assert row["active"] is True
    assert row["asset_path"] == f"/api/v1/mascots/{TEST_CODE}/image"
    assert bytes(row["image_data"]) == image


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_add_mascot_redelivery_is_idempotent(database_url: str) -> None:
    # A redelivered update carries the exact same document bytes.
    image = build_png()

    async def run() -> bool:
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await add_mascot(
                    session,
                    code=TEST_CODE,
                    name="Умка",
                    blurb="Тихий и загадочный",
                    unlock_threshold=411,
                    image_data=image,
                )
        finally:
            await engine.dispose()

    assert asyncio.run(run()) is False
    assert asyncio.run(count_mascots(database_url, TEST_CODE)) == 1


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_add_mascot_refuses_taken_code_without_changes(database_url: str) -> None:
    async def run() -> None:
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                with pytest.raises(MascotCodeTaken):
                    await add_mascot(
                        session,
                        code=TEST_CODE,
                        name="Другое имя",
                        blurb="Тихий и загадочный",
                        unlock_threshold=411,
                        image_data=build_png(),
                    )
        finally:
            await engine.dispose()

    asyncio.run(run())

    row = asyncio.run(read_mascot(database_url, TEST_CODE))
    assert row is not None
    assert row["name"] == "Умка"


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_add_mascot_refuses_taken_threshold(database_url: str) -> None:
    async def run() -> None:
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                with pytest.raises(ThresholdTaken):
                    await add_mascot(
                        session,
                        code=TEST_CODE_2,
                        name="Второй",
                        blurb="Тоже хороший",
                        unlock_threshold=411,
                        image_data=build_png(),
                    )
        finally:
            await engine.dispose()

    asyncio.run(run())
    assert asyncio.run(read_mascot(database_url, TEST_CODE_2)) is None


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_mascot_image_endpoint_serves_png_and_404_for_unknown(client: TestClient) -> None:
    response = client.get(f"/api/v1/mascots/{TEST_CODE}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "max-age" in response.headers.get("cache-control", "")

    missing = client.get("/api/v1/mascots/no-such-mascot/image")

    assert missing.status_code == 404
