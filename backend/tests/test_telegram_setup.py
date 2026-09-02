"""Tests for the Telegram Bot API setup commands (PH-803).

A fake aiogram ``Bot`` is injected through ``bot_factory`` so these tests need
no network access or real token. They cover argument parsing (default
``keep-pending`` vs explicit ``--drop-pending``), the assembled webhook URL,
and that no secret (bot token, webhook path, webhook secret) ever reaches
stdout/stderr.
"""

from unittest.mock import AsyncMock

import pytest
from aiogram.types import User, WebhookInfo

from app.core.config import Settings
from app.modules.telegram.setup import main

BOT_TOKEN = "123456:AAFakeTokenForTestsOnly"
WEBHOOK_SECRET = "test-webhook-secret-value"
WEBHOOK_PATH = "test-webhook-path-segment"


def _settings() -> Settings:
    return Settings(
        app_env="development",
        app_domain="https://app.example.com",
        bot_token=BOT_TOKEN,
        telegram_webhook_secret=WEBHOOK_SECRET,
        telegram_webhook_path=WEBHOOK_PATH,
        database_url="postgresql+asyncpg://pohvala:pw@localhost:5432/pohvala",
        cors_origins="https://app.example.com",
    )


class FakeSession:
    def __init__(self) -> None:
        self.close = AsyncMock()


class FakeBot:
    """Stand-in for ``aiogram.Bot`` that records calls instead of hitting Telegram."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.session = FakeSession()
        self.get_me = AsyncMock(
            return_value=User(id=1, is_bot=True, first_name="Pohvala", username="pohvala_bot")
        )
        self.set_webhook = AsyncMock(return_value=True)
        self.set_chat_menu_button = AsyncMock(return_value=True)
        self.get_webhook_info = AsyncMock(
            return_value=WebhookInfo(
                url=f"https://app.example.com/api/v1/telegram/{WEBHOOK_PATH}",
                has_custom_certificate=False,
                pending_update_count=3,
                last_error_message=None,
            )
        )


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.telegram.setup.get_settings", _settings)


def test_get_me_prints_username_without_token(capsys: pytest.CaptureFixture[str]) -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["get-me"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "pohvala_bot" in output
    assert BOT_TOKEN not in output
    fake_bot.session.close.assert_awaited_once()


def test_set_webhook_defaults_to_keep_pending() -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["set-webhook"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    fake_bot.set_webhook.assert_awaited_once_with(
        url=f"https://app.example.com/api/v1/telegram/{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        allowed_updates=["message"],
        drop_pending_updates=False,
    )


def test_set_webhook_drop_pending_flag_sets_true() -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["set-webhook", "--drop-pending"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    fake_bot.set_webhook.assert_awaited_once_with(
        url=f"https://app.example.com/api/v1/telegram/{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        allowed_updates=["message"],
        drop_pending_updates=True,
    )


def test_set_webhook_keep_pending_flag_sets_false() -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["set-webhook", "--keep-pending"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    fake_bot.set_webhook.assert_awaited_once_with(
        url=f"https://app.example.com/api/v1/telegram/{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        allowed_updates=["message"],
        drop_pending_updates=False,
    )


def test_set_webhook_rejects_both_flags_together() -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    argv = ["set-webhook", "--drop-pending", "--keep-pending"]
    with pytest.raises(SystemExit):
        main(argv, bot_factory=lambda token: fake_bot)

    fake_bot.set_webhook.assert_not_awaited()


def test_set_menu_button_targets_app_domain() -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["set-menu-button"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    fake_bot.set_chat_menu_button.assert_awaited_once()
    _, kwargs = fake_bot.set_chat_menu_button.call_args
    menu_button = kwargs["menu_button"]
    assert menu_button.type == "web_app"
    assert menu_button.web_app.url == "https://app.example.com"


def test_get_webhook_info_omits_path_and_secret(capsys: pytest.CaptureFixture[str]) -> None:
    fake_bot = FakeBot(BOT_TOKEN)

    exit_code = main(["get-webhook-info"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "app.example.com" in output
    assert "3" in output
    assert WEBHOOK_PATH not in output
    assert WEBHOOK_SECRET not in output


def test_get_webhook_info_redacts_path_inside_last_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_bot = FakeBot(BOT_TOKEN)
    fake_bot.get_webhook_info = AsyncMock(
        return_value=WebhookInfo(
            url=f"https://app.example.com/api/v1/telegram/{WEBHOOK_PATH}",
            has_custom_certificate=False,
            pending_update_count=0,
            last_error_message=f"Wrong response, url contained {WEBHOOK_PATH} somehow",
        )
    )

    exit_code = main(["get-webhook-info"], bot_factory=lambda token: fake_bot)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert WEBHOOK_PATH not in output


def test_no_command_exits_nonzero() -> None:
    with pytest.raises(SystemExit):
        main([], bot_factory=lambda token: FakeBot(BOT_TOKEN))
