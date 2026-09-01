from fastapi import APIRouter, HTTPException, Response

from app.api.dependencies import DatabaseSession, MascotRateLimited, TelegramAuth
from app.modules.mascots.schemas import (
    MascotActivated,
    MascotCollection,
    MascotPurchased,
)
from app.modules.mascots.service import (
    InsufficientStars,
    MascotLocked,
    MascotNotFound,
    NotOwned,
    UserNotFound,
    get_mascot_image,
    list_collection,
    purchase_mascot,
    set_active_mascot,
)

router = APIRouter()

_NO_SESSION = "Open a session before opening the collection"


@router.get(
    "/mascots/{code}/image",
    response_class=Response,
    responses={404: {"description": "Mascot image not found"}},
    # Deliberately public: catalog artwork is not user data and <img> tags
    # cannot send the Telegram authorization header. Seed mascots are already
    # public static assets; this endpoint serves admin-added ones (PH-405).
    include_in_schema=True,
)
async def get_mascot_image_endpoint(
    code: str,
    session: DatabaseSession,
) -> Response:
    image = await get_mascot_image(session, code=code)
    if image is None:
        raise HTTPException(status_code=404, detail="Mascot image not found")
    return Response(
        content=image,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/mascots",
    response_model=MascotCollection,
    responses={401: {"description": "Invalid Telegram authorization or unknown session"}},
)
async def list_mascots_endpoint(
    identity: TelegramAuth,
    session: DatabaseSession,
) -> MascotCollection:
    try:
        collection = await list_collection(session, telegram_id=identity.telegram_id)
    except UserNotFound:
        raise HTTPException(status_code=401, detail=_NO_SESSION) from None

    return MascotCollection.from_view(collection)


@router.post(
    "/mascots/{code}/purchase",
    response_model=MascotPurchased,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        404: {"description": "Mascot not found or not purchasable"},
        409: {"description": "Mascot is still locked or not enough stars"},
        429: {"description": "Too many requests"},
    },
)
async def purchase_mascot_endpoint(
    code: str,
    identity: MascotRateLimited,
    session: DatabaseSession,
) -> MascotPurchased:
    try:
        result = await purchase_mascot(session, telegram_id=identity.telegram_id, code=code)
    except UserNotFound:
        raise HTTPException(status_code=401, detail=_NO_SESSION) from None
    except MascotNotFound:
        raise HTTPException(status_code=404, detail="Mascot not found") from None
    except MascotLocked:
        raise HTTPException(
            status_code=409,
            detail="Keep noticing your days — this companion is still resting",
        ) from None
    except InsufficientStars:
        raise HTTPException(
            status_code=409,
            detail="A few more stars and this companion is yours",
        ) from None

    return MascotPurchased.from_result(result)


@router.put(
    "/mascots/{code}/active",
    response_model=MascotActivated,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        404: {"description": "Mascot not found"},
        409: {"description": "Mascot is not owned"},
        429: {"description": "Too many requests"},
    },
)
async def activate_mascot_endpoint(
    code: str,
    identity: MascotRateLimited,
    session: DatabaseSession,
) -> MascotActivated:
    try:
        await set_active_mascot(session, telegram_id=identity.telegram_id, code=code)
    except UserNotFound:
        raise HTTPException(status_code=401, detail=_NO_SESSION) from None
    except MascotNotFound:
        raise HTTPException(status_code=404, detail="Mascot not found") from None
    except NotOwned:
        raise HTTPException(
            status_code=409,
            detail="This companion is not in your collection yet",
        ) from None

    return MascotActivated(active_mascot=code)
