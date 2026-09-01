from uuid import UUID

from sqlalchemy import Uuid, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mascots.catalog import MASCOT_SEEDS
from app.modules.mascots.models import Mascot, MascotOwnership, MascotUnlock
from app.modules.stars.models import StarBalance, StarLedgerEntry
from app.modules.users.models import User


async def get_user(session: AsyncSession, *, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


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


async def list_active_catalog(session: AsyncSession) -> list[Mascot]:
    result = await session.execute(
        select(Mascot).where(Mascot.active.is_(True)).order_by(Mascot.sort_order)
    )
    return list(result.scalars().all())


async def get_mascot(session: AsyncSession, *, code: str) -> Mascot | None:
    result = await session.execute(select(Mascot).where(Mascot.code == code))
    return result.scalar_one_or_none()


async def find_by_unlock_threshold(
    session: AsyncSession,
    *,
    unlock_threshold: int,
) -> Mascot | None:
    result = await session.execute(
        select(Mascot).where(Mascot.unlock_threshold == unlock_threshold)
    )
    return result.scalar_one_or_none()


async def get_mascot_image_data(session: AsyncSession, *, code: str) -> bytes | None:
    result = await session.execute(select(Mascot.image_data).where(Mascot.code == code))
    return result.scalar_one_or_none()


async def next_sort_order(session: AsyncSession) -> int:
    result = await session.execute(select(func.max(Mascot.sort_order)))
    current = result.scalar_one_or_none()
    return (current or 0) + 1


async def owned_codes(session: AsyncSession, *, user_id: UUID) -> set[str]:
    result = await session.execute(
        select(MascotOwnership.mascot_code).where(MascotOwnership.user_id == user_id)
    )
    return set(result.scalars().all())


async def owns_mascot(session: AsyncSession, *, user_id: UUID, code: str) -> bool:
    result = await session.execute(
        select(MascotOwnership.mascot_code).where(
            MascotOwnership.user_id == user_id,
            MascotOwnership.mascot_code == code,
        )
    )
    return result.scalar_one_or_none() is not None


async def lock_balance_for_update(session: AsyncSession, *, user_id: UUID) -> int:
    """Read the spendable balance while holding a row lock.

    The `FOR UPDATE` lock serializes concurrent purchases for the same user so two
    requests can never spend the same stars twice. Missing balance rows only happen
    before a user has earned any star, where every priced purchase is unaffordable.
    """

    result = await session.execute(
        select(StarBalance.balance).where(StarBalance.user_id == user_id).with_for_update()
    )
    return result.scalar_one_or_none() or 0


async def debit_balance(session: AsyncSession, *, user_id: UUID, amount: int) -> None:
    await session.execute(
        update(StarBalance)
        .where(StarBalance.user_id == user_id)
        .values(balance=StarBalance.balance - amount, updated_at=func.now())
    )


async def record_purchase(
    session: AsyncSession,
    *,
    user_id: UUID,
    code: str,
    price: int,
) -> None:
    await session.execute(
        insert(MascotOwnership)
        .values(user_id=user_id, mascot_code=code, price_paid=price)
        .on_conflict_do_nothing(index_elements=["user_id", "mascot_code"])
    )
    await session.execute(
        insert(StarLedgerEntry).values(
            user_id=user_id, amount=-price, reason="purchase", local_date=None
        )
    )


async def set_active_mascot(session: AsyncSession, *, user_id: UUID, code: str) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(active_mascot_code=code)
    )
