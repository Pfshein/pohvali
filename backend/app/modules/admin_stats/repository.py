from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin_stats.models import UserActivityDay
from app.modules.praises.models import Praise
from app.modules.users.models import User


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    return moment.astimezone(UTC)


async def record_activity_day(
    session: AsyncSession,
    *,
    user_id: UUID,
    observed_at: datetime,
) -> None:
    """Record one opening without starting or committing a transaction."""
    observed_at = _as_utc(observed_at)
    statement = (
        insert(UserActivityDay)
        .values(
            user_id=user_id,
            activity_date=observed_at.date(),
            first_opened_at=observed_at,
            last_opened_at=observed_at,
            open_count=1,
        )
        .on_conflict_do_update(
            index_elements=[UserActivityDay.user_id, UserActivityDay.activity_date],
            set_={
                "open_count": UserActivityDay.open_count + 1,
                "last_opened_at": func.greatest(UserActivityDay.last_opened_at, observed_at),
            },
        )
    )
    await session.execute(statement)


async def get_period_stats(
    session: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    start_date: date,
    end_date: date,
) -> tuple[int, int, int]:
    """Return opened users, praised users, and praise count for one period."""
    opened = await session.scalar(
        select(func.count(func.distinct(UserActivityDay.user_id))).where(
            UserActivityDay.activity_date.between(start_date, end_date)
        )
    )
    praised = await session.scalar(
        select(func.count(func.distinct(Praise.user_id))).where(
            Praise.created_at >= start_at,
            Praise.created_at < end_at,
        )
    )
    praises = await session.scalar(
        select(func.count(Praise.id)).where(
            Praise.created_at >= start_at,
            Praise.created_at < end_at,
        )
    )
    return int(opened or 0), int(praised or 0), int(praises or 0)


async def get_all_time_stats(session: AsyncSession) -> tuple[int, int, int]:
    """Return all users, users with praise, and total praises."""
    users = await session.scalar(select(func.count(User.id)))
    praised_users = await session.scalar(
        select(func.count(func.distinct(Praise.user_id)))
    )
    praises = await session.scalar(select(func.count(Praise.id)))
    return int(users or 0), int(praised_users or 0), int(praises or 0)
