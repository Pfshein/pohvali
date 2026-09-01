from uuid import UUID

from sqlalchemy import Uuid, func, literal, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mascots.catalog import MASCOT_SEEDS
from app.modules.mascots.models import Mascot, MascotUnlock
from app.modules.stars.models import StarLedgerEntry


async def get_earned_daily_stars(session: AsyncSession, *, user_id: UUID) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(StarLedgerEntry.amount), 0)).where(
            StarLedgerEntry.user_id == user_id,
            StarLedgerEntry.reason == "daily",
        )
    )
    return int(result.scalar_one())


async def unlock_eligible_mascots(
    session: AsyncSession,
    *,
    user_id: UUID,
    earned_stars: int,
) -> list[str]:
    eligible = (
        select(
            literal(user_id, type_=Uuid),
            Mascot.code,
            Mascot.unlock_threshold,
        )
        .where(
            Mascot.active.is_(True),
            Mascot.starter.is_(False),
            Mascot.unlock_threshold.is_not(None),
            Mascot.unlock_threshold <= earned_stars,
        )
        .order_by(Mascot.unlock_threshold, Mascot.sort_order)
    )
    statement = (
        insert(MascotUnlock)
        .from_select(["user_id", "mascot_code", "threshold"], eligible)
        .on_conflict_do_nothing(index_elements=["user_id", "mascot_code"])
        .returning(MascotUnlock.mascot_code)
    )
    result = await session.execute(statement)
    unlocked = list(result.scalars().all())
    catalog_order = {mascot.code: mascot.sort_order for mascot in MASCOT_SEEDS}
    return sorted(unlocked, key=lambda code: catalog_order.get(code, 10_000))
