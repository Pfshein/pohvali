from app.modules.bot.messages import FORBIDDEN_TONE_WORDS
from app.modules.bot.service import build_start_reply

MINI_APP_URL = "https://app.example.com"


def start_update(*, text: str = "/start", chat_type: str = "private", chat_id: int = 555) -> dict:
    return {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "date": 1_700_000_000,
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
        },
    }


def test_start_in_private_chat_produces_greeting_with_mini_app_button() -> None:
    reply = build_start_reply(start_update(chat_id=777), mini_app_url=MINI_APP_URL)

    assert reply is not None
    assert reply.chat_id == 777
    assert reply.web_app_url == MINI_APP_URL
    assert reply.button_text
    assert reply.text


def test_start_greeting_keeps_a_calm_pressure_free_tone() -> None:
    reply = build_start_reply(start_update(), mini_app_url=MINI_APP_URL)

    assert reply is not None
    lowered = reply.text.casefold()
    for word in FORBIDDEN_TONE_WORDS:
        assert word.casefold() not in lowered


def test_start_command_accepts_bot_mention_and_deep_link_payload() -> None:
    for text in ("/start", "/start@PohvaliSebyaBot", "/start welcome", "  /start  "):
        assert build_start_reply(start_update(text=text), mini_app_url=MINI_APP_URL) is not None


def test_non_start_message_is_ignored() -> None:
    assert build_start_reply(start_update(text="hello"), mini_app_url=MINI_APP_URL) is None
    assert build_start_reply(start_update(text="/help"), mini_app_url=MINI_APP_URL) is None
    assert build_start_reply(start_update(text="/started"), mini_app_url=MINI_APP_URL) is None


def test_start_outside_private_chat_is_ignored() -> None:
    for chat_type in ("group", "supergroup", "channel"):
        update = start_update(chat_type=chat_type)
        assert build_start_reply(update, mini_app_url=MINI_APP_URL) is None


def test_updates_without_a_text_message_are_ignored() -> None:
    assert build_start_reply({"update_id": 1}, mini_app_url=MINI_APP_URL) is None
    assert build_start_reply(
        {"update_id": 1, "callback_query": {"id": "x"}}, mini_app_url=MINI_APP_URL
    ) is None
    photo_update = {
        "update_id": 1,
        "message": {"chat": {"id": 5, "type": "private"}, "photo": []},
    }
    assert build_start_reply(photo_update, mini_app_url=MINI_APP_URL) is None
