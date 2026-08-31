"""Register (or refresh) the Telegram webhook for this deployment.

Run once per environment after the backend is reachable over HTTPS:

    python scripts/set_telegram_webhook.py

Reads configuration from the backend Settings (`.env` / environment), so the
same BOT_TOKEN, APP_DOMAIN, TELEGRAM_WEBHOOK_PATH and TELEGRAM_WEBHOOK_SECRET
that the app uses are applied to Telegram. Only `message` updates are requested
because that is all the bot handles today.
"""

import asyncio
import sys

from aiogram import Bot

from app.core.config import get_settings


async def main() -> int:
    settings = get_settings()
    base = settings.app_domain.rstrip("/")
    webhook_url = f"{base}/api/v1/telegram/{settings.telegram_webhook_path}"

    bot = Bot(settings.bot_token)
    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.telegram_webhook_secret,
            allowed_updates=["message"],
            drop_pending_updates=True,
        )
    finally:
        await bot.session.close()

    # Do not print the secret path/token — only confirm the host it points at.
    print(f"Webhook set for host {settings.app_domain}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
