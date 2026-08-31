from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import DatabaseSession, PraiseRateLimited, TelegramAuth
from app.modules.praises.schemas import (
    MAX_CIPHERTEXT_BYTES,
    PraiseCreated,
    PraiseCreateRequest,
    PraiseEditRequest,
    PraiseEntry,
)
from app.modules.praises.service import (
    PraiseNotFound,
    UserNotFound,
    create_praise,
    delete_praise,
    list_day_praises,
    update_praise,
)

router = APIRouter()


@router.post(
    "/praises",
    response_model=PraiseCreated,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        413: {"description": "Encrypted praise exceeds the size limit"},
        429: {"description": "Too many requests"},
    },
)
async def create_praise_endpoint(
    payload: PraiseCreateRequest,
    identity: PraiseRateLimited,
    session: DatabaseSession,
) -> PraiseCreated:
    ciphertext = payload.ciphertext_bytes
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Encrypted praise is too large",
        )

    try:
        result = await create_praise(
            session,
            telegram_id=identity.telegram_id,
            ciphertext=ciphertext,
            iv=payload.iv_bytes,
        )
    except UserNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Open a session before saving praise",
        ) from None

    return PraiseCreated(
        id=result.id,
        local_date=result.local_date,
        star_awarded=result.star_awarded,
        balance=result.balance,
    )


@router.get(
    "/praises",
    response_model=list[PraiseEntry],
    responses={401: {"description": "Invalid Telegram authorization or unknown session"}},
)
async def list_praises_endpoint(
    identity: TelegramAuth,
    session: DatabaseSession,
    day: Annotated[date | None, Query(alias="date")] = None,
) -> list[PraiseEntry]:
    try:
        praises = await list_day_praises(
            session,
            telegram_id=identity.telegram_id,
            day=day,
        )
    except UserNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Open a session before reading praise",
        ) from None

    return [PraiseEntry.from_praise(praise) for praise in praises]


@router.patch(
    "/praises/{praise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        404: {"description": "Praise not found or not owned by the requester"},
        413: {"description": "Encrypted praise exceeds the size limit"},
    },
)
async def edit_praise_endpoint(
    praise_id: UUID,
    payload: PraiseEditRequest,
    identity: TelegramAuth,
    session: DatabaseSession,
) -> Response:
    ciphertext = payload.ciphertext_bytes
    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise HTTPException(status_code=413, detail="Encrypted praise is too large")

    try:
        await update_praise(
            session,
            telegram_id=identity.telegram_id,
            praise_id=praise_id,
            ciphertext=ciphertext,
            iv=payload.iv_bytes,
            sticker=payload.sticker,
        )
    except UserNotFound:
        raise HTTPException(
            status_code=401,
            detail="Open a session before editing praise",
        ) from None
    except PraiseNotFound:
        raise HTTPException(status_code=404, detail="Praise not found") from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/praises/{praise_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        404: {"description": "Praise not found or not owned by the requester"},
    },
)
async def delete_praise_endpoint(
    praise_id: UUID,
    identity: TelegramAuth,
    session: DatabaseSession,
) -> Response:
    try:
        await delete_praise(
            session,
            telegram_id=identity.telegram_id,
            praise_id=praise_id,
        )
    except UserNotFound:
        raise HTTPException(
            status_code=401,
            detail="Open a session before deleting praise",
        ) from None
    except PraiseNotFound:
        raise HTTPException(status_code=404, detail="Praise not found") from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)
