from datetime import date
from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.praises.models import Praise
from app.modules.stars.models import StarBalance, StarLedgerEntry
from app.modules.users.models import User


async def get_user(session: AsyncSession, *, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def insert_praise(
    session: AsyncSession,
    *,
    user_id: UUID,
    ciphertext: bytes,
    iv: bytes,
    local_date: date,
) -> Praise:
    statement = (
        insert(Praise)
        .values(user_id=user_id, body_ciphertext=ciphertext, iv=iv, local_date=local_date)
        .returning(Praise)
    )
    return (await session.execute(statement)).scalar_one()


async def try_award_daily_star(
    session: AsyncSession,
    *,
    user_id: UUID,
    local_date: date,
) -> bool:
    statement = (
        insert(StarLedgerEntry)
        .values(user_id=user_id, amount=1, reason="daily", local_date=local_date)
        .on_conflict_do_nothing(
            index_elements=["user_id", "local_date"],
            index_where=text("reason = 'daily'"),
        )
        .returning(StarLedgerEntry.id)
    )
    return (await session.execute(statement)).scalar_one_or_none() is not None


async def increment_balance(session: AsyncSession, *, user_id: UUID) -> None:
    statement = (
        insert(StarBalance)
        .values(user_id=user_id, balance=1)
        .on_conflict_do_update(
            index_elements=["user_id"],
            set_={"balance": StarBalance.balance + 1, "updated_at": func.now()},
        )
    )
    await session.execute(statement)


async def get_balance(session: AsyncSession, *, user_id: UUID) -> int:
    result = await session.execute(
        select(StarBalance.balance).where(StarBalance.user_id == user_id)
    )
    return result.scalar_one_or_none() or 0


async def list_praises_for_day(
    session: AsyncSession,
    *,
    user_id: UUID,
    day: date,
) -> list[Praise]:
    result = await session.execute(
        select(Praise)
        .where(Praise.user_id == user_id, Praise.local_date == day)
        .order_by(Praise.created_at)
    )
    return list(result.scalars().all())


async def update_praise(
    session: AsyncSession,
    *,
    user_id: UUID,
    praise_id: UUID,
    ciphertext: bytes,
    iv: bytes,
    sticker: str | None,
) -> bool:
    statement = (
        update(Praise)
        .where(Praise.id == praise_id, Praise.user_id == user_id)
        .values(body_ciphertext=ciphertext, iv=iv, sticker=sticker, updated_at=func.now())
        .returning(Praise.id)
    )
    return (await session.execute(statement)).scalar_one_or_none() is not None


async def delete_praise(session: AsyncSession, *, user_id: UUID, praise_id: UUID) -> bool:
    statement = (
        delete(Praise)
        .where(Praise.id == praise_id, Praise.user_id == user_id)
        .returning(Praise.id)
    )
    return (await session.execute(statement)).scalar_one_or_none() is not None


async def count_praises_by_day(
    session: AsyncSession,
    *,
    user_id: UUID,
    start: date,
    end: date,
) -> list[tuple[date, int]]:
    result = await session.execute(
        select(Praise.local_date, func.count().label("count"))
        .where(Praise.user_id == user_id, Praise.local_date.between(start, end))
        .group_by(Praise.local_date)
        .order_by(Praise.local_date)
    )
    return [(row.local_date, row.count) for row in result.all()]
