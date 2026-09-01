from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api import dependencies
from app.api.dependencies import enforce_praise_rate_limit, get_telegram_identity
from app.api.rate_limit import FixedWindowRateLimiter
from app.security.telegram import TelegramIdentity


def test_limiter_allows_up_to_max_then_denies() -> None:
    limiter = FixedWindowRateLimiter(max_requests=2, window_seconds=60, now=lambda: 100.0)

    assert limiter.allow("user") is True
    assert limiter.allow("user") is True
    assert limiter.allow("user") is False


def test_limiter_resets_after_the_window() -> None:
    clock = {"t": 0.0}
    limiter = FixedWindowRateLimiter(
        max_requests=1,
        window_seconds=60,
        now=lambda: clock["t"],
    )

    assert limiter.allow("user") is True
    assert limiter.allow("user") is False

    clock["t"] = 61.0
    assert limiter.allow("user") is True


def test_limiter_is_per_key() -> None:
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, now=lambda: 0.0)

    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_endpoint_dependency_returns_429_when_exceeded() -> None:
    from datetime import UTC, datetime

    application = FastAPI()
    application.dependency_overrides[get_telegram_identity] = lambda: TelegramIdentity(
        telegram_id=7, auth_date=datetime.now(UTC)
    )

    @application.post("/limited")
    def limited(
        identity: Annotated[TelegramIdentity, Depends(enforce_praise_rate_limit)],
    ) -> dict[str, int]:
        return {"telegram_id": identity.telegram_id}

    dependencies.praise_rate_limiter.max_requests = 1
    dependencies.praise_rate_limiter.reset()
    client = TestClient(application)
    try:
        first = client.post("/limited")
        second = client.post("/limited")
    finally:
        dependencies.praise_rate_limiter.max_requests = 60
        dependencies.praise_rate_limiter.reset()

    assert first.status_code == 200
    assert second.status_code == 429


def test_production_requires_https_mini_app_cors() -> None:
    from app.core.config import Settings

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            app_domain="https://app.example.com",
            cors_origins="http://localhost",
        )

    ok = Settings(
        app_env="production",
        app_domain="https://app.example.com",
        bot_token="123456:real-bot-token",
        telegram_webhook_secret="real-webhook-secret",
        telegram_webhook_path="real-webhook-path",
        database_url="postgresql+asyncpg://pohvala:strong-password@postgres:5432/pohvala",
        cors_origins="https://app.example.com",
    )
    assert ok.cors_origin_list == ["https://app.example.com"]


def test_production_requires_public_app_domain_in_cors() -> None:
    from app.core.config import Settings

    values = {
        "app_env": "production",
        "app_domain": "https://app.example.com",
        "bot_token": "123456:real-bot-token",
        "telegram_webhook_secret": "real-webhook-secret",
        "telegram_webhook_path": "real-webhook-path",
        "database_url": "postgresql+asyncpg://pohvala:strong-password@postgres:5432/pohvala",
        "cors_origins": "https://app.example.com",
    }

    with pytest.raises(ValueError, match="APP_DOMAIN"):
        Settings(**(values | {"app_domain": "https://localhost"}))

    with pytest.raises(ValueError, match="APP_DOMAIN"):
        Settings(**(values | {"cors_origins": "https://other.example.com"}))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bot_token", "dev-token"),
        ("bot_token", "replace-me"),
        ("telegram_webhook_secret", "dev-webhook-secret"),
        ("telegram_webhook_path", "replace-with-a-random-path"),
        (
            "database_url",
            "postgresql+asyncpg://pohvala:pohvala@postgres:5432/pohvala",
        ),
    ],
)
def test_production_rejects_placeholder_secrets(field: str, value: str) -> None:
    from app.core.config import Settings

    values = {
        "app_env": "production",
        "app_domain": "https://app.example.com",
        "bot_token": "123456:real-bot-token",
        "telegram_webhook_secret": "real-webhook-secret",
        "telegram_webhook_path": "real-webhook-path",
        "database_url": "postgresql+asyncpg://pohvala:strong-password@postgres:5432/pohvala",
        "cors_origins": "https://app.example.com",
        field: value,
    }

    with pytest.raises(ValueError, match="production secrets"):
        Settings(**values)


def test_cors_preflight_allows_put(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            response = client.options(
                "/api/v1/mascots/ava/active",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "PUT",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]
