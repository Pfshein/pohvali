from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin_stats import repository


@dataclass(frozen=True, slots=True)
class PeriodStats:
    opened_users: int
    praised_users: int
    praises: int

@dataclass(frozen=True, slots=True)
class StatsSnapshot:
    today: PeriodStats
    last_7_days: PeriodStats
    last_30_days: PeriodStats
    all_time: PeriodStats

def _period(now: datetime, days: int) -> tuple[datetime, datetime, date, date]:
    utc_now = now.astimezone(UTC)
    today = utc_now.date()
    start_day = today - timedelta(days=days - 1)
    end_day = today + timedelta(days=1)
    start_at = datetime.combine(start_day, time.min, tzinfo=UTC)
    end_at = datetime.combine(end_day, time.min, tzinfo=UTC)
    return start_at, end_at, start_day, today


async def get_stats_snapshot(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> StatsSnapshot:
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    async with session.begin():
        today_start, today_end, today_date, today_last = _period(moment, 1)
        week_start, week_end, week_date, week_last = _period(moment, 7)
        month_start, month_end, month_date, month_last = _period(moment, 30)
        today = PeriodStats(*(await repository.get_period_stats(
            session,
            start_at=today_start,
            end_at=today_end,
            start_date=today_date,
            end_date=today_last,
        )))
        week = PeriodStats(*(await repository.get_period_stats(
            session,
            start_at=week_start,
            end_at=week_end,
            start_date=week_date,
            end_date=week_last,
        )))
        month = PeriodStats(*(await repository.get_period_stats(
            session,
            start_at=month_start,
            end_at=month_end,
            start_date=month_date,
            end_date=month_last,
        )))
        users, praised_users, praises = await repository.get_all_time_stats(session)
    return StatsSnapshot(
        today=today,
        last_7_days=week,
        last_30_days=month,
        all_time=PeriodStats(users, praised_users, praises),
    )
