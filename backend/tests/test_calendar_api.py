from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_telegram_identity
from app.main import app
from app.security.telegram import TelegramIdentity


def override_identity() -> TelegramIdentity:
    return TelegramIdentity(telegram_id=4242, auth_date=datetime.now(UTC))


async def override_session() -> object:
    yield object()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_calendar_requires_authorization() -> None:
    response = TestClient(app).get("/api/v1/calendar?from=2026-09-01&to=2026-09-30")

    assert response.status_code == 401


def test_calendar_requires_both_bounds() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    response = TestClient(app).get(
        "/api/v1/calendar?from=2026-09-01",
        headers={"Authorization": "tma ignored"},
    )

    assert response.status_code == 422


def test_calendar_rejects_inverted_range() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    response = TestClient(app).get(
        "/api/v1/calendar?from=2026-09-30&to=2026-09-01",
        headers={"Authorization": "tma ignored"},
    )

    assert response.status_code == 422


def test_calendar_rejects_oversized_range() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    response = TestClient(app).get(
        "/api/v1/calendar?from=2020-01-01&to=2026-01-01",
        headers={"Authorization": "tma ignored"},
    )

    assert response.status_code == 422
