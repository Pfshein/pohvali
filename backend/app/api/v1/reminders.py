from fastapi import APIRouter, HTTPException

from app.api.dependencies import DatabaseSession, ReminderRateLimited, TelegramAuth
from app.modules.reminders.schemas import ReminderSettingsResponse, ReminderUpdateRequest
from app.modules.reminders.service import (
    UserNotFound,
    get_settings,
    set_enabled,
)

router = APIRouter()

_NO_SESSION = "Open a session before changing reminder settings"


@router.get(
    "/reminders",
    response_model=ReminderSettingsResponse,
    responses={401: {"description": "Invalid Telegram authorization or unknown session"}},
)
async def get_reminders_endpoint(
    identity: TelegramAuth,
    session: DatabaseSession,
) -> ReminderSettingsResponse:
    try:
        settings = await get_settings(session, telegram_id=identity.telegram_id)
    except UserNotFound:
        raise HTTPException(status_code=401, detail=_NO_SESSION) from None

    return ReminderSettingsResponse.from_settings(settings)


@router.put(
    "/reminders",
    response_model=ReminderSettingsResponse,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        429: {"description": "Too many requests"},
    },
)
async def update_reminders_endpoint(
    payload: ReminderUpdateRequest,
    identity: ReminderRateLimited,
    session: DatabaseSession,
) -> ReminderSettingsResponse:
    try:
        settings = await set_enabled(
            session, telegram_id=identity.telegram_id, enabled=payload.enabled
        )
    except UserNotFound:
        raise HTTPException(status_code=401, detail=_NO_SESSION) from None

    return ReminderSettingsResponse.from_settings(settings)
