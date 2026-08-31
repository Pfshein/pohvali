import base64
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_telegram_identity
from app.main import app
from app.security.telegram import TelegramIdentity


def override_identity() -> TelegramIdentity:
    from datetime import UTC, datetime

    return TelegramIdentity(telegram_id=4242, auth_date=datetime.now(UTC))


async def override_session() -> object:
    yield object()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_oversized_ciphertext_is_rejected_before_the_service() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    oversized = base64.b64encode(b"x" * 5000).decode()
    iv = base64.b64encode(bytes(12)).decode()

    with patch("app.api.v1.praises.create_praise", new=AsyncMock()) as service:
        response = TestClient(app).post(
            "/api/v1/praises",
            headers={"Authorization": "tma ignored"},
            json={"body_ciphertext": oversized, "iv": iv},
        )

    assert response.status_code == 413
    service.assert_not_called()


def test_missing_authorization_returns_401() -> None:
    response = TestClient(app).post(
        "/api/v1/praises",
        json={
            "body_ciphertext": base64.b64encode(b"abc").decode(),
            "iv": base64.b64encode(bytes(12)).decode(),
        },
    )

    assert response.status_code == 401


def test_list_requires_authorization() -> None:
    response = TestClient(app).get("/api/v1/praises")

    assert response.status_code == 401


def test_list_rejects_an_invalid_date() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    response = TestClient(app).get(
        "/api/v1/praises?date=not-a-date",
        headers={"Authorization": "tma ignored"},
    )

    assert response.status_code == 422


PRAISE_ID = "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d"


def test_edit_requires_authorization() -> None:
    response = TestClient(app).patch(
        f"/api/v1/praises/{PRAISE_ID}",
        json={
            "body_ciphertext": base64.b64encode(b"abc").decode(),
            "iv": base64.b64encode(bytes(12)).decode(),
        },
    )

    assert response.status_code == 401


def test_edit_rejects_oversized_ciphertext_before_the_service() -> None:
    app.dependency_overrides[get_telegram_identity] = override_identity
    app.dependency_overrides[get_db_session] = override_session

    oversized = base64.b64encode(b"x" * 5000).decode()
    iv = base64.b64encode(bytes(12)).decode()

    with patch("app.api.v1.praises.update_praise", new=AsyncMock()) as service:
        response = TestClient(app).patch(
            f"/api/v1/praises/{PRAISE_ID}",
            headers={"Authorization": "tma ignored"},
            json={"body_ciphertext": oversized, "iv": iv},
        )

    assert response.status_code == 413
    service.assert_not_called()


def test_delete_requires_authorization() -> None:
    response = TestClient(app).delete(f"/api/v1/praises/{PRAISE_ID}")

    assert response.status_code == 401
