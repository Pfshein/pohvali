from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession, TelegramAuth
from app.modules.praises.schemas import MAX_CALENDAR_SPAN_DAYS, CalendarDay
from app.modules.praises.service import UserNotFound, list_calendar

router = APIRouter()


@router.get(
    "/calendar",
    response_model=list[CalendarDay],
    responses={
        401: {"description": "Invalid Telegram authorization or unknown session"},
        422: {"description": "Missing or invalid date range"},
    },
)
async def calendar_endpoint(
    identity: TelegramAuth,
    session: DatabaseSession,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> list[CalendarDay]:
    if end < start or (end - start) > timedelta(days=MAX_CALENDAR_SPAN_DAYS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Calendar range is inverted or too large",
        )

    try:
        days = await list_calendar(
            session,
            telegram_id=identity.telegram_id,
            start=start,
            end=end,
        )
    except UserNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Open a session before reading the calendar",
        ) from None

    return [CalendarDay(local_date=day, count=count) for day, count in days]
