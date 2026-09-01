from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_telegram_identity
from app.main import app
from app.modules.mascots.service import (
    CollectionView,
    InsufficientStars,
    MascotLocked,
    MascotNotFound,
    MascotState,
    MascotView,
    NotOwned,
    PurchaseResult,
    UserNotFound,
)
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


def test_list_requires_authorization() -> None:
    response = TestClient(app).get("/api/v1/mascots")

    assert response.status_code == 401


def test_list_returns_collection_state() -> None:
    _authorize()
    view = CollectionView(
        balance=12,
        active_mascot="ava",
        mascots=(
            MascotView(
                code="ava",
                name="Авокадо Ава",
                blurb="Спокойная и тёплая",
                asset_path="/assets/mascots/ava.png",
                starter=True,
                price=None,
                state=MascotState.OWNED,
                unlocked=True,
                active=True,
            ),
            MascotView(
                code="tisha",
                name="Капибара Тиша",
                blurb="Добрая и невозмутимая",
                asset_path="/assets/mascots/tisha.png",
                starter=False,
                price=10,
                state=MascotState.AFFORDABLE,
                unlocked=True,
                active=False,
            ),
        ),
    )

    with patch("app.api.v1.mascots.list_collection", new=AsyncMock(return_value=view)):
        response = TestClient(app).get(
            "/api/v1/mascots", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 12
    assert body["active_mascot"] == "ava"
    assert body["mascots"][1] == {
        "code": "tisha",
        "name": "Капибара Тиша",
        "blurb": "Добрая и невозмутимая",
        "asset_path": "/assets/mascots/tisha.png",
        "starter": False,
        "price": 10,
        "state": "affordable",
        "unlocked": True,
        "active": False,
    }


def test_purchase_requires_authorization() -> None:
    response = TestClient(app).post("/api/v1/mascots/tisha/purchase")

    assert response.status_code == 401


def test_purchase_returns_debited_balance() -> None:
    _authorize()
    result = PurchaseResult(code="tisha", balance=2, newly_purchased=True)

    with patch("app.api.v1.mascots.purchase_mascot", new=AsyncMock(return_value=result)):
        response = TestClient(app).post(
            "/api/v1/mascots/tisha/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 200
    assert response.json() == {
        "code": "tisha",
        "state": "owned",
        "balance": 2,
        "newly_purchased": True,
    }


def test_repeat_purchase_reports_owned_without_debit() -> None:
    _authorize()
    result = PurchaseResult(code="tisha", balance=2, newly_purchased=False)

    with patch("app.api.v1.mascots.purchase_mascot", new=AsyncMock(return_value=result)):
        response = TestClient(app).post(
            "/api/v1/mascots/tisha/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 200
    assert response.json()["newly_purchased"] is False


def test_purchase_unknown_mascot_returns_404() -> None:
    _authorize()

    with patch("app.api.v1.mascots.purchase_mascot", new=AsyncMock(side_effect=MascotNotFound)):
        response = TestClient(app).post(
            "/api/v1/mascots/ghost/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 404


def test_purchase_locked_mascot_returns_409() -> None:
    _authorize()

    with patch("app.api.v1.mascots.purchase_mascot", new=AsyncMock(side_effect=MascotLocked)):
        response = TestClient(app).post(
            "/api/v1/mascots/bim/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 409


def test_purchase_without_enough_stars_returns_409() -> None:
    _authorize()

    with patch(
        "app.api.v1.mascots.purchase_mascot", new=AsyncMock(side_effect=InsufficientStars)
    ):
        response = TestClient(app).post(
            "/api/v1/mascots/lumi/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 409


def test_purchase_without_session_returns_401() -> None:
    _authorize()

    with patch("app.api.v1.mascots.purchase_mascot", new=AsyncMock(side_effect=UserNotFound)):
        response = TestClient(app).post(
            "/api/v1/mascots/tisha/purchase", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 401


def test_activate_requires_authorization() -> None:
    response = TestClient(app).put("/api/v1/mascots/tisha/active")

    assert response.status_code == 401


def test_activate_owned_mascot_succeeds() -> None:
    _authorize()

    with patch("app.api.v1.mascots.set_active_mascot", new=AsyncMock()):
        response = TestClient(app).put(
            "/api/v1/mascots/tisha/active", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 200
    assert response.json() == {"active_mascot": "tisha"}


def test_activate_unowned_mascot_returns_409() -> None:
    _authorize()

    with patch("app.api.v1.mascots.set_active_mascot", new=AsyncMock(side_effect=NotOwned)):
        response = TestClient(app).put(
            "/api/v1/mascots/bim/active", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 409


def test_activate_unknown_mascot_returns_404() -> None:
    _authorize()

    with patch(
        "app.api.v1.mascots.set_active_mascot", new=AsyncMock(side_effect=MascotNotFound)
    ):
        response = TestClient(app).put(
            "/api/v1/mascots/ghost/active", headers={"Authorization": "tma ignored"}
        )

    assert response.status_code == 404
