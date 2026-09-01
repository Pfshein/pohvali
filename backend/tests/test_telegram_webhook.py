import logging
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_reply_sender
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.bot.service import StartReply


async def override_session() -> object:
    yield object()

WEBHOOK_PATH = "s3cr3t-path"
WEBHOOK_SECRET = "s3cr3t-header-token"
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
SENTINEL_TEXT = "please-do-not-log-this-body"


class RecordingSender:
    def __init__(self) -> None:
        self.replies: list[StartReply] = []

    async def __call__(self, reply: StartReply) -> None:
        self.replies.append(reply)


def build_client() -> tuple[TestClient, RecordingSender]:
    sender = RecordingSender()
    settings = Settings(
        app_domain="https://app.example.com",
        telegram_webhook_path=WEBHOOK_PATH,
        telegram_webhook_secret=WEBHOOK_SECRET,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_reply_sender] = lambda: sender
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), sender


def teardown_function() -> None:
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_reply_sender, None)
    app.dependency_overrides.pop(get_db_session, None)


def start_update(*, text: str = "/start") -> dict:
    return {
        "update_id": 42,
        "message": {
            "message_id": 1,
            "chat": {"id": 909, "type": "private"},
            "text": text,
        },
    }


def test_valid_secret_and_start_command_triggers_one_reply() -> None:
    client, sender = build_client()

    with patch("app.api.v1.telegram.record_dm_available", new=AsyncMock()) as record:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=start_update(),
        )

    assert response.status_code == 200
    assert len(sender.replies) == 1
    assert sender.replies[0].chat_id == 909
    assert sender.replies[0].web_app_url == "https://app.example.com"
    # A private-chat /start records that the bot may DM this user (PH-501).
    record.assert_awaited_once()
    assert record.await_args.kwargs == {"telegram_id": 909}


def test_non_start_update_records_no_dm_availability() -> None:
    client, sender = build_client()

    with patch("app.api.v1.telegram.record_dm_available", new=AsyncMock()) as record:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=start_update(text="just chatting"),
        )

    assert response.status_code == 200
    assert sender.replies == []
    record.assert_not_awaited()


def test_wrong_secret_header_is_rejected_and_does_not_dispatch() -> None:
    client, sender = build_client()

    response = client.post(
        f"/api/v1/telegram/{WEBHOOK_PATH}",
        headers={SECRET_HEADER: "forged"},
        json=start_update(),
    )

    assert response.status_code == 403
    assert sender.replies == []


def test_missing_secret_header_is_rejected() -> None:
    client, sender = build_client()

    response = client.post(f"/api/v1/telegram/{WEBHOOK_PATH}", json=start_update())

    assert response.status_code == 403
    assert sender.replies == []


def test_wrong_path_is_not_found_and_does_not_dispatch() -> None:
    client, sender = build_client()

    response = client.post(
        "/api/v1/telegram/guessed-wrong",
        headers={SECRET_HEADER: WEBHOOK_SECRET},
        json=start_update(),
    )

    assert response.status_code == 404
    assert sender.replies == []


def test_update_body_is_not_written_to_logs(caplog) -> None:
    client, _ = build_client()

    with caplog.at_level(logging.DEBUG):
        client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=start_update(text=SENTINEL_TEXT),
        )

    assert SENTINEL_TEXT not in caplog.text
