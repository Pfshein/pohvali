import logging
import struct
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session, get_file_downloader, get_reply_sender
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.bot.service import StartReply


async def override_session() -> object:
    yield object()

WEBHOOK_PATH = "s3cr3t-path"
WEBHOOK_SECRET = "s3cr3t-header-token"
SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
SENTINEL_TEXT = "please-do-not-log-this-body"
ADMIN_ID = 700


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
        telegram_admin_ids=str(ADMIN_ID),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_reply_sender] = lambda: sender
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), sender


def teardown_function() -> None:
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_reply_sender, None)
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_file_downloader, None)


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


def valid_png_bytes() -> bytes:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + chunk_type + payload + b"\x00\x00\x00\x00"

    ihdr = struct.pack(">IIBBBBB", 512, 512, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


def add_mascot_update(*, from_id: int = ADMIN_ID) -> dict:
    return {
        "update_id": 43,
        "message": {
            "message_id": 2,
            "date": 1_700_000_000,
            "chat": {"id": from_id, "type": "private"},
            "from": {"id": from_id, "is_bot": False},
            "caption": "/add_mascot test_umka 411 | Умка | Тихий и загадочный",
            "document": {
                "file_id": "AgAC-secret-file-id",
                "file_unique_id": "unique",
                "mime_type": "image/png",
                "file_size": 2048,
            },
        },
    }


def override_downloader(payload: bytes | Exception) -> list[str]:
    calls: list[str] = []

    if isinstance(payload, Exception):

        async def downloader(file_id: str) -> bytes:
            calls.append(file_id)
            raise payload

    else:

        async def downloader(file_id: str) -> bytes:
            calls.append(file_id)
            return payload

    app.dependency_overrides[get_file_downloader] = lambda: downloader
    return calls


def test_admin_add_mascot_creates_mascot_and_replies_with_preview() -> None:
    client, sender = build_client()
    downloads = override_downloader(valid_png_bytes())

    with patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=True)) as service:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(),
        )

    assert response.status_code == 200
    assert downloads == ["AgAC-secret-file-id"]
    assert service.await_count == 1
    kwargs = service.await_args.kwargs
    assert kwargs["code"] == "test_umka"
    assert kwargs["unlock_threshold"] == 411
    assert kwargs["name"] == "Умка"
    assert kwargs["blurb"] == "Тихий и загадочный"
    assert kwargs["image_data"] == valid_png_bytes()

    assert len(sender.replies) == 1
    reply = sender.replies[0]
    assert reply.chat_id == ADMIN_ID
    assert reply.document_file_id == "AgAC-secret-file-id"
    assert "Умка" in reply.text


def test_redelivered_add_mascot_replies_calmly_without_second_insert() -> None:
    client, sender = build_client()
    override_downloader(valid_png_bytes())

    with patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=False)):
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(),
        )

    assert response.status_code == 200
    assert len(sender.replies) == 1
    assert "уже есть" in sender.replies[0].text
    assert sender.replies[0].document_file_id == "AgAC-secret-file-id"


def test_non_admin_add_mascot_is_denied_without_side_effects() -> None:
    client, sender = build_client()
    override_downloader(valid_png_bytes())

    with patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=True)) as service:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(from_id=42),
        )

    assert response.status_code == 200
    service.assert_not_awaited()
    assert len(sender.replies) == 1
    assert "администратору" in sender.replies[0].text
    assert sender.replies[0].document_file_id is None


def test_invalid_png_is_refused_without_touching_catalog() -> None:
    client, sender = build_client()
    override_downloader(b"definitely-not-a-png")

    with patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=True)) as service:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(),
        )

    assert response.status_code == 200
    service.assert_not_awaited()
    assert len(sender.replies) == 1
    assert "png" in sender.replies[0].text.casefold()


def test_download_failure_replies_retry_message() -> None:
    client, sender = build_client()
    override_downloader(RuntimeError("telegram is down"))

    with patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=True)) as service:
        response = client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(),
        )

    assert response.status_code == 200
    service.assert_not_awaited()
    assert len(sender.replies) == 1
    assert "ещё раз" in sender.replies[0].text


def test_add_mascot_logs_never_contain_file_id_or_ids(caplog) -> None:
    client, _ = build_client()
    override_downloader(valid_png_bytes())

    with (
        caplog.at_level(logging.DEBUG),
        patch("app.api.v1.telegram.add_mascot", new=AsyncMock(return_value=True)),
    ):
        client.post(
            f"/api/v1/telegram/{WEBHOOK_PATH}",
            headers={SECRET_HEADER: WEBHOOK_SECRET},
            json=add_mascot_update(),
        )

    assert "AgAC-secret-file-id" not in caplog.text
    assert str(ADMIN_ID) not in caplog.text
    assert "Умка" not in caplog.text
