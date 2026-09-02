from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import AdminUser, get_telegram_identity
from app.core.config import Settings, get_settings
from app.core.db import get_db_session
from app.security.telegram import TelegramIdentity


@pytest.mark.parametrize("role", ["user", "admin"])
def test_dependency_denies_non_admin_and_allows_admin(role: str) -> None:
    user = SimpleNamespace(role=role)
    application = FastAPI()
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    database_session = SimpleNamespace(begin=MagicMock(return_value=transaction))

    async def session():
        yield database_session

    application.dependency_overrides[get_db_session] = session
    identity = TelegramIdentity(telegram_id=700, auth_date=datetime.now(UTC))
    application.dependency_overrides[get_telegram_identity] = lambda: identity

    @application.get("/admin")
    async def endpoint(_: AdminUser) -> dict[str, str]:
        return {"status": "ok"}

    with patch("app.api.dependencies.get_user_by_telegram_id", new=AsyncMock(return_value=user)):
        response = TestClient(application).get("/admin")

    assert response.status_code == (200 if role == "admin" else 403)
    database_session.begin.assert_called_once_with()
    if role != "admin":
        assert response.json() == {"detail": "Admin access required"}


def test_dependency_denies_unknown_user_with_same_response() -> None:
    application = FastAPI()
    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=None)
    transaction.__aexit__ = AsyncMock(return_value=None)
    database_session = SimpleNamespace(begin=MagicMock(return_value=transaction))

    async def session():
        yield database_session

    application.dependency_overrides[get_db_session] = session
    application.dependency_overrides[get_telegram_identity] = lambda: TelegramIdentity(
        telegram_id=700, auth_date=datetime.now(UTC)
    )

    @application.get("/admin")
    async def endpoint(_: AdminUser) -> dict[str, str]:
        return {"status": "ok"}

    with patch("app.api.dependencies.get_user_by_telegram_id", new=AsyncMock(return_value=None)):
        response = TestClient(application).get("/admin")

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}


def test_invalid_identity_returns_401_before_role_lookup() -> None:
    application = FastAPI()

    async def session():
        yield object()

    application.dependency_overrides[get_db_session] = session
    application.dependency_overrides[get_settings] = lambda: Settings(bot_token="dev-token")

    @application.get("/admin")
    async def endpoint(_: AdminUser) -> dict[str, str]:
        return {"status": "ok"}

    with patch("app.api.dependencies.get_user_by_telegram_id", new=AsyncMock()) as lookup:
        response = TestClient(application).get("/admin")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Telegram authorization"}
    lookup.assert_not_awaited()
