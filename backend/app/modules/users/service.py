from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin_stats.repository import record_activity_day
from app.modules.users.models import User, UserRole
from app.modules.users.repository import (
    delete_user_by_telegram_id,
    get_user_by_telegram_id,
    update_user_role,
    upsert_user,
)


class UserNotFound(Exception):
    """The requested Telegram account has not opened the app yet."""


async def open_session(
    session: AsyncSession,
    *,
    telegram_id: int,
    timezone: str,
    observed_at: datetime | None = None,
) -> User:
    observed_at = observed_at or datetime.now(UTC)
    async with session.begin():
        user = await upsert_user(
            session,
            telegram_id=telegram_id,
            timezone=timezone,
        )
        await record_activity_day(session, user_id=user.id, observed_at=observed_at)
        return user


async def erase_account(
    session: AsyncSession,
    *,
    telegram_id: int,
) -> None:
    """Delete the account; related rows cascade at the database level."""
    async with session.begin():
        await delete_user_by_telegram_id(session, telegram_id=telegram_id)


async def set_user_role(
    session: AsyncSession,
    *,
    telegram_id: int,
    role: UserRole,
) -> User:
    role = UserRole(role)
    async with session.begin():
        user = await update_user_role(session, telegram_id=telegram_id, role=role)
        if user is None:
            raise UserNotFound
        return user


async def is_admin_user(session: AsyncSession, *, telegram_id: int) -> bool:
    # The webhook may call a write service immediately afterwards. Finish this
    # authorization read first so that service can open its own transaction.
    async with session.begin():
        user = await get_user_by_telegram_id(session, telegram_id=telegram_id)
        return user is not None and user.role == UserRole.ADMIN.value
