from pydantic import BaseModel

from app.modules.mascots.service import (
    CollectionView,
    MascotState,
    MascotView,
    PurchaseResult,
)


class MascotItem(BaseModel):
    code: str
    name: str
    blurb: str
    asset_path: str
    starter: bool
    price: int | None
    state: MascotState
    unlocked: bool
    active: bool

    @classmethod
    def from_view(cls, view: MascotView) -> "MascotItem":
        return cls(
            code=view.code,
            name=view.name,
            blurb=view.blurb,
            asset_path=view.asset_path,
            starter=view.starter,
            price=view.price,
            state=view.state,
            unlocked=view.unlocked,
            active=view.active,
        )


class MascotCollection(BaseModel):
    balance: int
    active_mascot: str | None
    mascots: list[MascotItem]

    @classmethod
    def from_view(cls, view: CollectionView) -> "MascotCollection":
        return cls(
            balance=view.balance,
            active_mascot=view.active_mascot,
            mascots=[MascotItem.from_view(item) for item in view.mascots],
        )


class MascotPurchased(BaseModel):
    code: str
    state: MascotState
    balance: int
    newly_purchased: bool

    @classmethod
    def from_result(cls, result: PurchaseResult) -> "MascotPurchased":
        return cls(
            code=result.code,
            state=MascotState.OWNED,
            balance=result.balance,
            newly_purchased=result.newly_purchased,
        )


class MascotActivated(BaseModel):
    active_mascot: str
