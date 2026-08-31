from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.repository import upsert_user


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
