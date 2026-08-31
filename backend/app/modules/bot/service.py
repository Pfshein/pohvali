"""Pure webhook update handling.

Given a raw Telegram update (already authenticated by the webhook secret) this
module decides whether a reply is owed and what it should contain. It performs
no I/O so the domain behaviour stays unit-testable without a network or a bot
token.
"""

from dataclasses import dataclass

from app.modules.bot.messages import OPEN_BUTTON_TEXT, START_GREETING


@dataclass(frozen=True, slots=True)
class StartReply:
    chat_id: int
    text: str
    web_app_url: str
    button_text: str


def build_start_reply(update: dict, *, mini_app_url: str) -> StartReply | None:
    """Return the greeting reply for a private-chat ``/start``, else ``None``."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return None

    chat_id = chat.get("id")
    if type(chat_id) is not int:
        return None

    text = message.get("text")
    if not isinstance(text, str) or not _is_start_command(text):
        return None

    return StartReply(
        chat_id=chat_id,
        text=START_GREETING,
        web_app_url=mini_app_url,
        button_text=OPEN_BUTTON_TEXT,
    )


def _is_start_command(text: str) -> bool:
    first, _, _ = text.strip().partition(" ")
    command, _, _ = first.partition("@")
    return command == "/start"
