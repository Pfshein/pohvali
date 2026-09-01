import asyncio

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.dialects import postgresql

from app.models import MascotUnlock
from app.modules.mascots.repository import unlock_eligible_mascots


def test_unlock_is_unique_per_user_and_mascot() -> None:
    table = MascotUnlock.__table__

    assert set(table.c.keys()) == {"user_id", "mascot_code", "threshold", "unlocked_at"}
    assert isinstance(table.c.user_id.type, Uuid)
    assert isinstance(table.c.mascot_code.type, String)
    assert isinstance(table.c.threshold.type, Integer)
    assert isinstance(table.c.unlocked_at.type, DateTime)
    assert table.primary_key.columns.keys() == ["user_id", "mascot_code"]


def test_unlock_foreign_keys_cascade_with_user_and_catalog() -> None:
    foreign_keys = {
        column.name: next(iter(column.foreign_keys))
        for column in (MascotUnlock.__table__.c.user_id, MascotUnlock.__table__.c.mascot_code)
    }

    assert foreign_keys["user_id"].column.table.name == "users"
    assert foreign_keys["user_id"].ondelete == "CASCADE"
    assert foreign_keys["mascot_code"].column.table.name == "mascots"
    assert foreign_keys["mascot_code"].ondelete == "CASCADE"


def test_unlock_query_uses_threshold_and_conflict_safe_insert() -> None:
    class RecordingSession:
        statements: list = []

        async def execute(self, statement):
            self.statements.append(statement)

            class Result:
                @staticmethod
                def scalars():
                    return Result()

                @staticmethod
                def all() -> list[str]:
                    return []

            return Result()

    session = RecordingSession()
    asyncio.run(
        unlock_eligible_mascots(  # type: ignore[arg-type]
            session,
            user_id="00000000-0000-0000-0000-000000000001",  # type: ignore[arg-type]
            earned_stars=30,
        )
    )

    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "unlock_threshold <=" in sql
    assert "ON CONFLICT (user_id, mascot_code) DO NOTHING" in sql
