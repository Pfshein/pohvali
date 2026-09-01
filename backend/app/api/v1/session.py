from fastapi import APIRouter, status

from app.api.dependencies import DatabaseSession, SessionRateLimited
from app.modules.users.schemas import SessionRequest, UserProfile
from app.modules.users.service import erase_account, open_session

router = APIRouter()


@router.post(
    "/session",
    response_model=UserProfile,
    responses={
        401: {"description": "Invalid Telegram authorization"},
        429: {"description": "Too many requests"},
    },
)
async def create_session(
    payload: SessionRequest,
    identity: SessionRateLimited,
    session: DatabaseSession,
) -> UserProfile:
    user = await open_session(
        session,
        telegram_id=identity.telegram_id,
        timezone=payload.timezone,
    )
    return UserProfile.model_validate(user)


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Account data erased (idempotent)"},
        401: {"description": "Invalid Telegram authorization"},
        429: {"description": "Too many requests"},
    },
)
async def delete_session(
    identity: SessionRateLimited,
    session: DatabaseSession,
) -> None:
    await erase_account(session, telegram_id=identity.telegram_id)
