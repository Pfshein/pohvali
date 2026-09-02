"""Telegram Bot API setup commands (PH-803).

Moved from ``scripts/set_telegram_webhook.py`` and extended so
``scripts/deploy.sh`` can drive the whole Telegram configuration surface
through the backend package instead of a bind-mounted script:
``getMe`` / ``setWebhook`` / ``setChatMenuButton`` / ``getWebhookInfo``.

Configuration comes from the same ``app.core.config.get_settings()`` the
running backend uses (``.env`` / process environment), so this always talks
about the deployment it runs inside. Output never includes the bot token,
the webhook secret, or the (unguessable) webhook path segment — only enough
to confirm the setup worked.

Entry point:

    python -m app.modules.telegram.setup <get-me|set-webhook|set-menu-button|get-webhook-info>
"""

import argparse
import asyncio
import sys
from collections.abc import Callable
from urllib.parse import urlsplit

from aiogram import Bot
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app.core.config import Settings, get_settings

# A callable so tests can inject a fake bot without touching the network or a
# real token. Defaults to the real aiogram ``Bot`` constructor.
BotFactory = Callable[[str], Bot]

_ALLOWED_UPDATES = ["message"]


def webhook_url(settings: Settings) -> str:
    base = settings.app_domain.rstrip("/")
    return f"{base}/api/v1/telegram/{settings.telegram_webhook_path}"


async def get_me(bot: Bot) -> int:
    me = await bot.get_me()
    print(f"Bot OK: @{me.username}")
    return 0


async def set_webhook(bot: Bot, settings: Settings, *, drop_pending: bool) -> int:
    await bot.set_webhook(
        url=webhook_url(settings),
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=_ALLOWED_UPDATES,
        drop_pending_updates=drop_pending,
    )
    mode = "dropped" if drop_pending else "kept"
    print(f"Webhook set for host {settings.app_domain} (pending updates {mode})")
    return 0


async def set_menu_button(bot: Bot, settings: Settings) -> int:
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Open",
            web_app=WebAppInfo(url=settings.app_domain.rstrip("/")),
        )
    )
    print(f"Menu button set for host {settings.app_domain}")
    return 0


def _host_only(url: str) -> str:
    """Drop path/query so an unset or misconfigured webhook path never prints."""
    if not url:
        return ""
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _redact_secrets(text: str | None, settings: Settings) -> str | None:
    """Defensive redaction: Telegram error text should not echo our secrets,
    but never trust upstream text to stay that way."""
    if not text:
        return text
    redacted = text
    for secret in (settings.telegram_webhook_path, settings.telegram_webhook_secret):
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    return redacted


async def get_webhook_info(bot: Bot, settings: Settings) -> int:
    info = await bot.get_webhook_info()
    print(f"Webhook host: {_host_only(info.url) or '(not set)'}")
    print(f"Pending updates: {info.pending_update_count}")
    last_error = _redact_secrets(info.last_error_message, settings)
    print(f"Last error: {last_error or 'none'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.modules.telegram.setup")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("get-me", help="Confirm the bot token is valid (getMe).")

    set_webhook_parser = subparsers.add_parser(
        "set-webhook", help="Register the Telegram webhook (setWebhook)."
    )
    pending_group = set_webhook_parser.add_mutually_exclusive_group()
    pending_group.add_argument(
        "--drop-pending",
        dest="drop_pending",
        action="store_true",
        help="Discard updates queued before the webhook is (re)registered. "
        "Only safe on first-run bootstrap.",
    )
    pending_group.add_argument(
        "--keep-pending",
        dest="drop_pending",
        action="store_false",
        help="Keep updates queued before the webhook is (re)registered (default).",
    )
    set_webhook_parser.set_defaults(drop_pending=False)

    subparsers.add_parser(
        "set-menu-button", help="Point the chat menu button at the Mini App."
    )
    subparsers.add_parser(
        "get-webhook-info", help="Print webhook status without secrets."
    )

    return parser


async def _dispatch(args: argparse.Namespace, bot: Bot, settings: Settings) -> int:
    if args.command == "get-me":
        return await get_me(bot)
    if args.command == "set-webhook":
        return await set_webhook(bot, settings, drop_pending=args.drop_pending)
    if args.command == "set-menu-button":
        return await set_menu_button(bot, settings)
    if args.command == "get-webhook-info":
        return await get_webhook_info(bot, settings)
    raise AssertionError(f"unhandled command: {args.command}")  # pragma: no cover


async def _run(argv: list[str] | None, bot_factory: BotFactory) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    bot = bot_factory(settings.bot_token)
    try:
        return await _dispatch(args, bot, settings)
    finally:
        await bot.session.close()


def main(argv: list[str] | None = None, *, bot_factory: BotFactory = Bot) -> int:
    return asyncio.run(_run(argv, bot_factory))


if __name__ == "__main__":
    sys.exit(main())
