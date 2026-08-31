from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    def _guard_production_cors(self) -> "Settings":
        if self.app_env != "production":
            return self

        origins = self.cors_origin_list
        if not origins or any(
            not origin.startswith("https://") or "localhost" in origin for origin in origins
        ):
            raise ValueError(
                "production CORS_ORIGINS must list only https Mini App origins (no localhost)"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
