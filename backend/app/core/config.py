from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_PLACEHOLDERS = {
    "",
    "dev-token",
    "dev-webhook-secret",
    "dev-webhook-path",
    "pohvala",
    "replace-me",
    "replace-with-a-random-secret",
    "replace-with-a-random-path",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_domain: str = "https://localhost"
    bot_token: str = "dev-token"
    telegram_webhook_secret: str = "dev-webhook-secret"
    telegram_webhook_path: str = "dev-webhook-path"
    database_url: str = "postgresql+asyncpg://pohvala:pohvala@localhost:5432/pohvala"
    cors_origins: str = "http://localhost:5173"
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        if self.app_env != "production":
            return self

        app_domain = self.app_domain.rstrip("/")
        if not app_domain.startswith("https://") or "localhost" in app_domain:
            raise ValueError(
                "production APP_DOMAIN must be the public https Mini App origin"
            )

        origins = self.cors_origin_list
        if not origins or any(
            not origin.startswith("https://") or "localhost" in origin for origin in origins
        ):
            raise ValueError(
                "production CORS_ORIGINS must list only https Mini App origins (no localhost)"
            )
        if app_domain not in {origin.rstrip("/") for origin in origins}:
            raise ValueError("production APP_DOMAIN must be listed in CORS_ORIGINS")

        database_password = make_url(self.database_url).password or ""
        secret_values = (
            self.bot_token,
            self.telegram_webhook_secret,
            self.telegram_webhook_path,
            database_password,
        )
        if any(value.casefold() in _PLACEHOLDERS for value in secret_values):
            raise ValueError("production secrets must not use development placeholders")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
