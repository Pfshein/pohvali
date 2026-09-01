"""Delivery of bot replies through the Telegram Bot API.

Kept behind a small protocol so the webhook endpoint depends on an interface
that tests can substitute without any network access or a valid bot token.
"""

from typing import Protocol


class BotReply(Protocol):
    """The minimal reply surface the sender needs.

    ``StartReply`` and ``AdminReply`` both satisfy it structurally; optional
    attributes (``web_app_url``/``button_text`` for a Mini App button,
    ``document_file_id`` for a captioned document echo) are read duck-typed.
    """

    chat_id: int
    text: str


class ReplySender(Protocol):
    async def __call__(self, reply: BotReply) -> None: ...


class AiogramReplySender:
    """Send a text reply, optionally with a Mini App button or a document echo."""

    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token

    async def __call__(self, reply: BotReply) -> None:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

        bot = Bot(self._bot_token)
        try:
            document_file_id = getattr(reply, "document_file_id", None)
            if document_file_id is not None:
                await bot.send_document(
                    chat_id=reply.chat_id,
                    document=document_file_id,
                    caption=reply.text,
                )
                return

            web_app_url = getattr(reply, "web_app_url", None)
            markup = None
            if web_app_url is not None:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=getattr(reply, "button_text", "Открыть"),
                                web_app=WebAppInfo(url=web_app_url),
                            )
                        ]
                    ]
                )
            await bot.send_message(
                chat_id=reply.chat_id,
                text=reply.text,
                reply_markup=markup,
            )
        finally:
            await bot.session.close()
