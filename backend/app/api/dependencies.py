from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rate_limit import FixedWindowRateLimiter
from app.core.config import Settings, get_settings
from app.core.db import get_db_session
from app.modules.bot.sender import AiogramReplySender, ReplySender
from app.security.telegram import InvalidInitData, TelegramIdentity, validate_init_data

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
telegram_authorization = APIKeyHeader(
    name="Authorization",
    scheme_name="TelegramMiniApp",
    description="Telegram Mini App header: tma <initDataRaw>",
    auto_error=False,
)


def get_telegram_identity(
    settings: SettingsDependency,
    authorization: Annotated[str | None, Security(telegram_authorization)],
) -> TelegramIdentity:
    scheme, separator, init_data = (authorization or "").partition(" ")
    if scheme.casefold() != "tma" or not separator or not init_data:
        raise _unauthorized()

    try:
        return validate_init_data(init_data, settings.bot_token)
    except (InvalidInitData, ValueError):
        raise _unauthorized() from None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Telegram authorization",
        headers={"WWW-Authenticate": "tma"},
    )


TelegramAuth = Annotated[TelegramIdentity, Depends(get_telegram_identity)]


def get_reply_sender(settings: SettingsDependency) -> ReplySender:
    return AiogramReplySender(settings.bot_token)


ReplySenderDependency = Annotated[ReplySender, Depends(get_reply_sender)]

session_rate_limiter = FixedWindowRateLimiter(max_requests=30, window_seconds=60)
praise_rate_limiter = FixedWindowRateLimiter(max_requests=60, window_seconds=60)
mascot_rate_limiter = FixedWindowRateLimiter(max_requests=30, window_seconds=60)
reminder_rate_limiter = FixedWindowRateLimiter(max_requests=30, window_seconds=60)


def _enforce(limiter: FixedWindowRateLimiter, identity: TelegramIdentity) -> TelegramIdentity:
    if not limiter.allow(str(identity.telegram_id)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please slow down",
        )
    return identity


def enforce_session_rate_limit(identity: TelegramAuth) -> TelegramIdentity:
    return _enforce(session_rate_limiter, identity)


def enforce_praise_rate_limit(identity: TelegramAuth) -> TelegramIdentity:
    return _enforce(praise_rate_limiter, identity)


def enforce_mascot_rate_limit(identity: TelegramAuth) -> TelegramIdentity:
    return _enforce(mascot_rate_limiter, identity)


def enforce_reminder_rate_limit(identity: TelegramAuth) -> TelegramIdentity:
    return _enforce(reminder_rate_limiter, identity)


SessionRateLimited = Annotated[TelegramIdentity, Depends(enforce_session_rate_limit)]
PraiseRateLimited = Annotated[TelegramIdentity, Depends(enforce_praise_rate_limit)]
MascotRateLimited = Annotated[TelegramIdentity, Depends(enforce_mascot_rate_limit)]
ReminderRateLimited = Annotated[TelegramIdentity, Depends(enforce_reminder_rate_limit)]
