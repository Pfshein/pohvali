import asyncio
import base64
import hashlib
import hmac
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.main import app
from app.modules.users.service import open_session
from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"
BOT_TOKEN = "123456:TEST-TOKEN"
TEST_TELEGRAM_IDS = (8_001_001, 8_001_002, 8_001_003)
DELETION_MASCOT_CODE = "test_privacy_mascot"
USER_DATA_TABLES = (
    "users",
    "praises",
    "star_ledger",
    "star_balances",
    "reminder_states",
    "mascot_unlocks",
    "mascot_ownership",
)


def signed_init_data(*, telegram_id: int) -> str:
    values = {
        "auth_date": str(int(datetime.now(UTC).timestamp())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {
                "id": telegram_id,
                "first_name": "Must not be persisted",
                "username": "private",
                "language_code": "ru",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


async def delete_test_users(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM users WHERE telegram_id = ANY(:telegram_ids)"),
                {"telegram_ids": list(TEST_TELEGRAM_IDS)},
            )
            await connection.execute(
                text("DELETE FROM mascots WHERE code = :code"),
                {"code": DELETION_MASCOT_CODE},
            )
    finally:
        await engine.dispose()


async def seed_deletion_extras(database_url: str, telegram_id: int) -> None:
    """Insert reminder state and mascot ownership rows the API cannot create here."""
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            user_id = (
                await connection.execute(
                    text("SELECT id FROM users WHERE telegram_id = :telegram_id"),
                    {"telegram_id": telegram_id},
                )
            ).scalar_one()
            await connection.execute(
                text(
                    "INSERT INTO reminder_states (user_id, phase) "
                    "VALUES (:user_id, 'active')"
                ),
                {"user_id": user_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO mascots "
                    "(code, name, blurb, asset_path, starter, active, sort_order) "
                    "VALUES (:code, 'Privacy test', 'deletion fixture', "
                    "'/assets/privacy-test.png', false, true, 999)"
                ),
                {"code": DELETION_MASCOT_CODE},
            )
            await connection.execute(
                text(
                    "INSERT INTO mascot_ownership (user_id, mascot_code, price_paid) "
                    "VALUES (:user_id, :code, 0)"
                ),
                {"user_id": user_id, "code": DELETION_MASCOT_CODE},
            )
    finally:
        await engine.dispose()


async def count_user_rows(database_url: str, telegram_id: int) -> dict[str, int]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            user_id = (
                await connection.execute(
                    text("SELECT id FROM users WHERE telegram_id = :telegram_id"),
                    {"telegram_id": telegram_id},
                )
            ).scalar_one_or_none()
            if user_id is None:
                return {table: 0 for table in USER_DATA_TABLES}
            counts: dict[str, int] = {}
            for table in USER_DATA_TABLES:
                column = "id" if table == "users" else "user_id"
                counts[table] = int(
                    (
                        await connection.execute(
                            text(
                                f"SELECT count(*) FROM {table} "
                                f"WHERE {column} = :user_id"
                            ),
                            {"user_id": user_id},
                        )
                    ).scalar_one()
                )
            return counts
    finally:
        await engine.dispose()


async def read_test_user(database_url: str, telegram_id: int) -> list[object]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return list(
                (
                    await connection.execute(
                        text(
                            "SELECT id, telegram_id, timezone, role "
                            "FROM users WHERE telegram_id = :telegram_id"
                        ),
                        {"telegram_id": telegram_id},
                    )
                ).all()
            )
    finally:
        await engine.dispose()


async def open_two_sessions_concurrently(
    database_url: str,
    telegram_id: int,
) -> tuple[object, object]:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def open_once(timezone: str) -> object:
        async with session_factory() as session:
            user = await open_session(
                session,
                telegram_id=telegram_id,
                timezone=timezone,
            )
            return user.id

    try:
        first, second = await asyncio.gather(
            open_once("UTC"),
            open_once("Europe/Moscow"),
        )
        return first, second
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


@pytest.fixture(scope="module")
def client(database_url: str) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="test",
        bot_token=BOT_TOKEN,
        database_url=database_url,
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_session_is_idempotent_and_updates_timezone(
    client: TestClient,
    database_url: str,
) -> None:
    headers = {
        "Authorization": f"tma {signed_init_data(telegram_id=TEST_TELEGRAM_IDS[0])}"
    }

    first = client.post("/api/v1/session", headers=headers, json={"timezone": "UTC"})
    second = client.post(
        "/api/v1/session",
        headers=headers,
        json={"timezone": "Europe/Moscow"},
    )

    assert first.status_code == 200
    assert set(first.json()) == {"id", "timezone", "role"}
    assert first.json()["role"] == "user"
    assert first.json()["timezone"] == "UTC"
    assert second.status_code == 200
    assert second.json() == {
        "id": first.json()["id"],
        "timezone": "Europe/Moscow",
        "role": "user",
    }

    rows = asyncio.run(read_test_user(database_url, TEST_TELEGRAM_IDS[0]))
    assert len(rows) == 1
    assert rows[0].id.hex == first.json()["id"].replace("-", "")
    assert rows[0].telegram_id == TEST_TELEGRAM_IDS[0]
    assert rows[0].timezone == "Europe/Moscow"
    assert rows[0].role == "user"


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_invalid_timezone_does_not_create_user(
    client: TestClient,
    database_url: str,
) -> None:
    response = client.post(
        "/api/v1/session",
        headers={
            "Authorization": f"tma {signed_init_data(telegram_id=TEST_TELEGRAM_IDS[1])}"
        },
        json={"timezone": "Mars/Olympus"},
    )

    assert response.status_code == 422
    assert asyncio.run(read_test_user(database_url, TEST_TELEGRAM_IDS[1])) == []


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_concurrent_first_open_creates_one_user(database_url: str) -> None:
    first_id, second_id = asyncio.run(
        open_two_sessions_concurrently(database_url, TEST_TELEGRAM_IDS[2])
    )

    rows = asyncio.run(read_test_user(database_url, TEST_TELEGRAM_IDS[2]))
    assert first_id == second_id
    assert len(rows) == 1
    assert rows[0].id == first_id


def test_invalid_telegram_authorization_returns_401() -> None:
    response = TestClient(app).post(
        "/api/v1/session",
        headers={"Authorization": "tma auth_date=1&hash=tampered"},
        json={"timezone": "UTC"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Telegram authorization"}


def test_openapi_documents_required_telegram_authorization() -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/session"]["post"]

    assert operation["security"] == [{"TelegramMiniApp": []}]
    assert "401" in operation["responses"]
    assert schema["components"]["securitySchemes"]["TelegramMiniApp"] == {
        "type": "apiKey",
        "description": "Telegram Mini App header: tma <initDataRaw>",
        "in": "header",
        "name": "Authorization",
    }


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_delete_session_erases_user_and_all_related_data(
    client: TestClient,
    database_url: str,
) -> None:
    headers = {
        "Authorization": f"tma {signed_init_data(telegram_id=TEST_TELEGRAM_IDS[0])}"
    }
    assert (
        client.post("/api/v1/session", headers=headers, json={"timezone": "UTC"}).status_code
        == 200
    )
    praise = client.post(
        "/api/v1/praises",
        headers=headers,
        json={
            "body_ciphertext": base64.b64encode(b"opaque-ciphertext").decode(),
            "iv": base64.b64encode(b"0123456789ab").decode(),
        },
    )
    assert praise.status_code == 201
    asyncio.run(seed_deletion_extras(database_url, TEST_TELEGRAM_IDS[0]))

    before = asyncio.run(count_user_rows(database_url, TEST_TELEGRAM_IDS[0]))
    assert before["users"] == 1
    assert before["praises"] == 1
    assert before["star_ledger"] == 1
    assert before["star_balances"] == 1
    assert before["reminder_states"] == 1
    assert before["mascot_ownership"] == 1

    response = client.delete("/api/v1/session", headers=headers)

    assert response.status_code == 204
    after = asyncio.run(count_user_rows(database_url, TEST_TELEGRAM_IDS[0]))
    assert after == {table: 0 for table in USER_DATA_TABLES}


@pytest.mark.skipif(not RUN_DATABASE_TESTS, reason="requires isolated PostgreSQL")
def test_delete_session_is_idempotent_without_existing_profile(
    client: TestClient,
    database_url: str,
) -> None:
    response = client.delete(
        "/api/v1/session",
        headers={
            "Authorization": f"tma {signed_init_data(telegram_id=TEST_TELEGRAM_IDS[1])}"
        },
    )

    assert response.status_code == 204
    assert asyncio.run(read_test_user(database_url, TEST_TELEGRAM_IDS[1])) == []


def test_delete_session_requires_valid_authorization() -> None:
    response = TestClient(app).delete(
        "/api/v1/session",
        headers={"Authorization": "tma auth_date=1&hash=tampered"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Telegram authorization"}
