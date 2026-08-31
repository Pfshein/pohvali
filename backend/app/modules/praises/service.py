from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.praises import repository as repo


class UserNotFound(Exception):
    """The authenticated Telegram id has no stored user (no session opened yet)."""


class PraiseNotFound(Exception):
    """The praise does not exist or is not owned by the requester."""


@dataclass(frozen=True, slots=True)
class PraiseResult:
    id: UUID
    local_date: date
    star_awarded: bool
    balance: int


def local_date_in_timezone(timezone: str, moment: datetime) -> date:
    return moment.astimezone(ZoneInfo(timezone)).date()


async def create_praise(
    session: AsyncSession,
    *,
    telegram_id: int,
    ciphertext: bytes,
    iv: bytes,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> PraiseResult:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        local_date = local_date_in_timezone(user.timezone, now())
        praise = await repo.insert_praise(
            session,
            user_id=user.id,
            ciphertext=ciphertext,
            iv=iv,
            local_date=local_date,
        )
        star_awarded = await repo.try_award_daily_star(
            session,
            user_id=user.id,
            local_date=local_date,
        )
        if star_awarded:
            await repo.increment_balance(session, user_id=user.id)
        balance = await repo.get_balance(session, user_id=user.id)

    return PraiseResult(
        id=praise.id,
        local_date=local_date,
        star_awarded=star_awarded,
        balance=balance,
    )


async def list_day_praises(
    session: AsyncSession,
    *,
    telegram_id: int,
    day: date | None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list:
    user = await repo.get_user(session, telegram_id=telegram_id)
    if user is None:
        raise UserNotFound

    target = day or local_date_in_timezone(user.timezone, now())
    return await repo.list_praises_for_day(session, user_id=user.id, day=target)


async def update_praise(
    session: AsyncSession,
    *,
    telegram_id: int,
    praise_id: UUID,
    ciphertext: bytes,
    iv: bytes,
    sticker: str | None,
) -> None:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        updated = await repo.update_praise(
            session,
            user_id=user.id,
            praise_id=praise_id,
            ciphertext=ciphertext,
            iv=iv,
            sticker=sticker,
        )
        if not updated:
            raise PraiseNotFound


async def delete_praise(
    session: AsyncSession,
    *,
    telegram_id: int,
    praise_id: UUID,
) -> None:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        deleted = await repo.delete_praise(session, user_id=user.id, praise_id=praise_id)
        if not deleted:
            raise PraiseNotFound


async def list_calendar(
    session: AsyncSession,
    *,
    telegram_id: int,
    start: date,
    end: date,
) -> list[tuple[date, int]]:
    user = await repo.get_user(session, telegram_id=telegram_id)
    if user is None:
        raise UserNotFound

    return await repo.count_praises_by_day(session, user_id=user.id, start=start, end=end)
