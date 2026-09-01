"""Mascot collection: catalog state, purchases, and active selection.

The star economy has two independent axes. `unlock_threshold` gates *eligibility*
against lifetime earned daily stars (monotonic, see PH-402); the spendable `balance`
gates *affordability* and is debited on purchase. Starter mascots are free and owned
by everyone implicitly, so they are never stored in `mascot_ownership` and never cost
stars.
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mascots import repository as repo
from app.modules.praises import repository as praise_repo


class UserNotFound(Exception):
    """The authenticated Telegram id has no stored user (no session opened yet)."""


class MascotNotFound(Exception):
    """The mascot code is unknown, inactive, or not purchasable."""


class MascotLocked(Exception):
    """The mascot is still locked: the user has not earned enough daily stars."""


class InsufficientStars(Exception):
    """The user does not have enough spendable stars to buy the mascot."""


class NotOwned(Exception):
    """The user tried to activate a mascot they do not own."""


class MascotState(StrEnum):
    OWNED = "owned"
    AFFORDABLE = "affordable"
    LOCKED = "locked"


@dataclass(frozen=True, slots=True)
class MascotView:
    code: str
    name: str
    blurb: str
    asset_path: str
    starter: bool
    price: int | None
    state: MascotState
    unlocked: bool
    active: bool


@dataclass(frozen=True, slots=True)
class CollectionView:
    balance: int
    active_mascot: str | None
    mascots: tuple[MascotView, ...]


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    code: str
    balance: int
    newly_purchased: bool


def _is_owned(*, starter: bool, code: str, owned: set[str]) -> bool:
    return starter or code in owned


async def list_collection(session: AsyncSession, *, telegram_id: int) -> CollectionView:
    user = await repo.get_user(session, telegram_id=telegram_id)
    if user is None:
        raise UserNotFound

    catalog = await repo.list_active_catalog(session)
    owned = await repo.owned_codes(session, user_id=user.id)
    earned = await repo.get_earned_daily_stars(session, user_id=user.id)
    balance = await praise_repo.get_balance(session, user_id=user.id)

    views: list[MascotView] = []
    for mascot in catalog:
        owned_here = _is_owned(starter=mascot.starter, code=mascot.code, owned=owned)
        price = None if mascot.starter else mascot.unlock_threshold
        unlocked = (
            True
            if mascot.starter
            else mascot.unlock_threshold is not None and earned >= mascot.unlock_threshold
        )
        if owned_here:
            state = MascotState.OWNED
        elif unlocked and price is not None and balance >= price:
            state = MascotState.AFFORDABLE
        else:
            state = MascotState.LOCKED
        views.append(
            MascotView(
                code=mascot.code,
                name=mascot.name,
                blurb=mascot.blurb,
                asset_path=mascot.asset_path,
                starter=mascot.starter,
                price=price,
                state=state,
                unlocked=unlocked,
                active=user.active_mascot_code == mascot.code,
            )
        )

    return CollectionView(
        balance=balance,
        active_mascot=user.active_mascot_code,
        mascots=tuple(views),
    )


async def purchase_mascot(
    session: AsyncSession,
    *,
    telegram_id: int,
    code: str,
) -> PurchaseResult:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        mascot = await repo.get_mascot(session, code=code)
        if mascot is None or not mascot.active or mascot.starter or mascot.unlock_threshold is None:
            raise MascotNotFound

        price = mascot.unlock_threshold
        earned = await repo.get_earned_daily_stars(session, user_id=user.id)
        if earned < price:
            raise MascotLocked

        # Lock the balance row before reading ownership so concurrent purchases
        # for the same user serialize and can never spend the same stars twice.
        balance = await repo.lock_balance_for_update(session, user_id=user.id)

        if await repo.owns_mascot(session, user_id=user.id, code=code):
            return PurchaseResult(code=code, balance=balance, newly_purchased=False)

        if balance < price:
            raise InsufficientStars

        await repo.debit_balance(session, user_id=user.id, amount=price)
        await repo.record_purchase(session, user_id=user.id, code=code, price=price)
        return PurchaseResult(code=code, balance=balance - price, newly_purchased=True)


async def set_active_mascot(
    session: AsyncSession,
    *,
    telegram_id: int,
    code: str,
) -> None:
    async with session.begin():
        user = await repo.get_user(session, telegram_id=telegram_id)
        if user is None:
            raise UserNotFound

        mascot = await repo.get_mascot(session, code=code)
        if mascot is None or not mascot.active:
            raise MascotNotFound

        owned = _is_owned(
            starter=mascot.starter,
            code=code,
            owned=await repo.owned_codes(session, user_id=user.id),
        )
        if not owned:
            raise NotOwned

        await repo.set_active_mascot(session, user_id=user.id, code=code)
