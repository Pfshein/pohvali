"""Delivery of reminder pushes through the Telegram Bot API.

Behind a small protocol so the delivery pipeline stays testable without a
network or a bot token. Telegram's own rate limiting surfaces as
``ReminderThrottled`` carrying ``retry_after`` seconds, which the pipeline
honours with backoff.
"""

from typing import Protocol


class ReminderThrottled(Exception):
    """Telegram asked us to slow down; wait ``retry_after`` seconds."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"throttled for {retry_after}s")
        self.retry_after = retry_after


class ReminderUnavailable(Exception):
    """Telegram confirms that this private chat can no longer receive messages."""


class ReminderSender(Protocol):
    async def __call__(self, *, chat_id: int, text: str) -> None: ...


class AiogramReminderSender:
    """Send a reminder with the inline button that opens the Mini App."""

    def __init__(self, bot_token: str, mini_app_url: str, button_text: str) -> None:
        self._bot_token = bot_token
        self._mini_app_url = mini_app_url
        self._button_text = button_text

    async def __call__(self, *, chat_id: int, text: str) -> None:
        from aiogram import Bot
        from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

        bot = Bot(self._bot_token)
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=self._button_text,
                                web_app=WebAppInfo(url=self._mini_app_url),
                            )
                        ]
                    ]
                ),
            )
        except TelegramRetryAfter as error:
            raise ReminderThrottled(error.retry_after) from error
        except TelegramForbiddenError as error:
            raise ReminderUnavailable from error
        finally:
            await bot.session.close()
