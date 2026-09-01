import asyncio

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects import postgresql

from app.models import Mascot
from app.modules.mascots.catalog import MASCOT_SEEDS
from app.modules.mascots.seed import seed_mascot_catalog


def test_mascot_model_has_stable_catalog_fields() -> None:
    columns = Mascot.__table__.c

    assert set(columns.keys()) == {
        "code",
        "name",
        "blurb",
        "asset_path",
        "starter",
        "unlock_threshold",
        "sort_order",
        "active",
    }
    assert isinstance(columns.code.type, String)
    assert columns.code.primary_key is True
    assert isinstance(columns.starter.type, Boolean)
    assert isinstance(columns.unlock_threshold.type, Integer)
    assert isinstance(columns.sort_order.type, Integer)


def test_catalog_has_six_unique_codes_and_three_starters() -> None:
    assert len(MASCOT_SEEDS) == 6
    assert len({mascot.code for mascot in MASCOT_SEEDS}) == 6
    assert [mascot.code for mascot in MASCOT_SEEDS if mascot.starter] == ["ava", "pol", "mira"]
    assert {
        mascot.unlock_threshold: mascot.code
        for mascot in MASCOT_SEEDS
        if mascot.unlock_threshold is not None
    } == {10: "tisha", 30: "lumi", 100: "bim"}


def test_seed_uses_upsert_and_is_safe_to_repeat() -> None:
    class RecordingSession:
        statements: list = []

        async def execute(self, statement) -> None:
            self.statements.append(statement)

    session = RecordingSession()
    asyncio.run(seed_mascot_catalog(session))  # type: ignore[arg-type]
    asyncio.run(seed_mascot_catalog(session))  # type: ignore[arg-type]

    assert len(session.statements) == 2
    sql = str(session.statements[0].compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (code) DO UPDATE" in sql
