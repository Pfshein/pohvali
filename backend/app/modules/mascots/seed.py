import asyncio
from dataclasses import asdict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session_factory
from app.modules.mascots.catalog import MASCOT_SEEDS
from app.modules.mascots.models import Mascot


async def seed_mascot_catalog(session: AsyncSession) -> None:
    rows = [asdict(seed) for seed in MASCOT_SEEDS]
    statement = insert(Mascot).values(rows)
    update_columns = {
        column: getattr(statement.excluded, column)
        for column in (
            "name",
            "blurb",
            "asset_path",
            "starter",
            "unlock_threshold",
            "sort_order",
            "active",
        )
    }
    await session.execute(
        statement.on_conflict_do_update(index_elements=[Mascot.code], set_=update_columns)
    )


async def _main() -> None:
    async with get_session_factory()() as session, session.begin():
        await seed_mascot_catalog(session)


if __name__ == "__main__":
    asyncio.run(_main())
