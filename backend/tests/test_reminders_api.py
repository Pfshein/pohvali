from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_telegram_identity
from app.main import app
from app.modules.reminders.service import ReminderSettings, UserNotFound
from app.modules.reminders.state import ReminderPhase
from app.security.telegram import TelegramIdentity


def override_identity() -> TelegramIdentity:
    return TelegramIdentity(telegram_id=4242, auth_date=datetime.now(UTC))


async def override_session() -> object:
    yield object()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _authorize() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session


def test_get_requires_authorization() -> None:
    response = TestClient(app).get("/api/v1/reminders")

    assert response.status_code == 401


def test_get_returns_settings_without_leaking_phase() -> None:
    _authorize()
    settings = ReminderSettings(enabled=True, dm_available=True, phase=ReminderPhase.ACTIVE)

    with patch("app.api.v1.reminders.get_settings", new=AsyncMock(return_value=settings)):
        response = TestClient(app).get(
            "/api/v1/reminders", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "dm_available": True}


def test_get_without_session_returns_401() -> None:
    _authorize()

    with patch("app.api.v1.reminders.get_settings", new=AsyncMock(side_effect=UserNotFound)):
        response = TestClient(app).get(
            "/api/v1/reminders", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 401


def test_put_requires_authorization() -> None:
    response = TestClient(app).put("/api/v1/reminders", json={"enabled": False})

    assert response.status_code == 401


def test_put_disables_reminders() -> None:
    _authorize()
    settings = ReminderSettings(enabled=False, dm_available=True, phase=ReminderPhase.ACTIVE)

    with patch(
        "app.api.v1.reminders.set_enabled", new=AsyncMock(return_value=settings)
    ) as service:
        response = TestClient(app).put(
            "/api/v1/reminders",
            headers={"Authorization": "tma ignored"},
            json={"enabled": False},
        )

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "dm_available": True}
    assert service.await_args.kwargs == {"telegram_id": 4242, "enabled": False}


def test_put_rejects_a_missing_enabled_flag() -> None:
    _authorize()

    response = TestClient(app).put(
        "/api/v1/reminders",
        headers={"Authorization": "tma ignored"},
        json={},
    )

    assert response.status_code == 422


def test_put_without_session_returns_401() -> None:
    _authorize()

    with patch("app.api.v1.reminders.set_enabled", new=AsyncMock(side_effect=UserNotFound)):
        response = TestClient(app).put(
            "/api/v1/reminders",
            headers={"Authorization": "tma ignored"},
            json={"enabled": True},
        )

    assert response.status_code == 401
