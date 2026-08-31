"""Delivery of bot replies through the Telegram Bot API.

Kept behind a small protocol so the webhook endpoint depends on an interface
that tests can substitute without any network access or a valid bot token.
"""

from typing import Protocol

from app.modules.bot.service import StartReply


class ReplySender(Protocol):
    async def __call__(self, reply: StartReply) -> None: ...


class AiogramReplySender:
    """Send a reply with an inline button that opens the Mini App."""

    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token

    async def __call__(self, reply: StartReply) -> None:
        from aiogram import Bot
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

        bot = Bot(self._bot_token)
        try:
            await bot.send_message(
                chat_id=reply.chat_id,
                text=reply.text,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=reply.button_text,
                                web_app=WebAppInfo(url=reply.web_app_url),
                            )
                        ]
                    ]
                ),
            )
        finally:
            await bot.session.close()
