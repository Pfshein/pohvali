from fastapi import APIRouter

from app.api.dependencies import DatabaseSession, SessionRateLimited
from app.modules.users.schemas import SessionRequest, UserProfile
from app.modules.users.service import open_session

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
