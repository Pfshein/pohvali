from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.repository import delete_user_by_telegram_id, upsert_user


async def open_session(
    session: AsyncSession,
    *,
    telegram_id: int,
    timezone: str,
) -> User:
    async with session.begin():
        return await upsert_user(
            session,
            telegram_id=telegram_id,
            timezone=timezone,
        )


async def erase_account(
    session: AsyncSession,
    *,
    telegram_id: int,
) -> None:
    """Delete the account; related rows cascade at the database level."""
    async with session.begin():
        await delete_user_by_telegram_id(session, telegram_id=telegram_id)
