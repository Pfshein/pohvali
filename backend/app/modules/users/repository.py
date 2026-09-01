from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def upsert_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    timezone: str,
) -> User:
    statement = (
        insert(User)
        .values(telegram_id=telegram_id, timezone=timezone)
        .on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={"timezone": timezone},
        )
        .returning(User)
    )
    result = await session.execute(statement)
    return result.scalar_one()


async def delete_user_by_telegram_id(
    session: AsyncSession,
    *,
    telegram_id: int,
) -> bool:
    statement = (
        delete(User).where(User.telegram_id == telegram_id).returning(User.id)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None
