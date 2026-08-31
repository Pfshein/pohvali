# Praise Schema and Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `praises` table that stores only encrypted bodies (`body_ciphertext`/`iv` as `BYTEA`), a server-owned `local_date`, creation/update timestamps, and a `(user_id, local_date)` index — with no plaintext column.

**Architecture:** A new `app.modules.praises.models.Praise` ORM model on the shared `Base`, registered in `app/models.py` so Alembic's `env.py` metadata sees it. A forward Alembic revision creates the table and composite index; `user_id` is a `CASCADE` foreign key to `users.id` (supports the future account-deletion path).

**Tech Stack:** SQLAlchemy 2 async, Alembic, PostgreSQL 17, Pytest.

**Spec:** `docs/backlog.md` — `PH-203 · P0 · Praise schema и миграция`; `docs/product-brief.md` invariants 3, 4, 7, 8.

---

## Global Constraints

- Columns exactly: `id, user_id, body_ciphertext, iv, local_date, created_at, updated_at`. No plaintext body/text column.
- `body_ciphertext` and `iv` are `LargeBinary` (`BYTEA`), both `NOT NULL` — backend treats them as opaque bytes.
- `local_date` is `Date`, `NOT NULL`, has no client-supplied default (the service computes it from the user's timezone in PH-204).
- Composite index on `(user_id, local_date)` named `ix_praises_user_id_local_date`.
- `user_id` → `users.id`, `NOT NULL`, `ON DELETE CASCADE`.
- Migration upgrades a clean DB to head and downgrades cleanly (drop index + table).
- No sticker/reason columns yet (YAGNI — added when PH-204/PH-301 need them).

---

### Task 1: Praise ORM model

**Files:**
- Create: `backend/app/modules/praises/__init__.py` (empty)
- Create: `backend/app/modules/praises/models.py`
- Test: `backend/tests/test_praise_model.py`

- [ ] **Step 1: Write the failing model tests**

```python
from datetime import date, datetime

from sqlalchemy import Date, DateTime, LargeBinary, Uuid

from app.modules.praises.models import Praise


def test_praise_persists_only_ciphertext_and_never_plaintext() -> None:
    columns = set(Praise.__table__.columns.keys())

    assert columns == {
        "id",
        "user_id",
        "body_ciphertext",
        "iv",
        "local_date",
        "created_at",
        "updated_at",
    }
    assert columns.isdisjoint({"body", "text", "plaintext", "body_plaintext"})


def test_ciphertext_and_iv_are_required_opaque_bytes() -> None:
    body = Praise.__table__.c.body_ciphertext
    iv = Praise.__table__.c.iv

    assert isinstance(body.type, LargeBinary)
    assert body.nullable is False
    assert isinstance(iv.type, LargeBinary)
    assert iv.nullable is False


def test_local_date_is_server_owned_required_date() -> None:
    local_date = Praise.__table__.c.local_date

    assert isinstance(local_date.type, Date)
    assert local_date.nullable is False
    assert local_date.default is None
    assert local_date.server_default is None


def test_user_id_is_a_required_cascade_foreign_key() -> None:
    user_id = Praise.__table__.c.user_id

    assert isinstance(user_id.type, Uuid)
    assert user_id.nullable is False
    foreign_key = next(iter(user_id.foreign_keys))
    assert foreign_key.column.table.name == "users"
    assert foreign_key.ondelete == "CASCADE"


def test_timestamps_are_timezone_aware_with_now_defaults() -> None:
    created_at = Praise.__table__.c.created_at
    updated_at = Praise.__table__.c.updated_at

    for column in (created_at, updated_at):
        assert isinstance(column.type, DateTime)
        assert column.type.timezone is True
        assert column.nullable is False
        assert str(column.server_default.arg) == "now()"


def test_calendar_index_covers_user_and_local_date() -> None:
    index_columns = {
        tuple(column.name for column in index.columns)
        for index in Praise.__table__.indexes
    }

    assert ("user_id", "local_date") in index_columns


def test_types_are_importable() -> None:
    # guard against unused-import lint noise while documenting the domain types
    assert date and datetime
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `cd backend && python -m pytest tests/test_praise_model.py -q`
Expected: FAIL — `app.modules.praises.models` does not exist.

- [ ] **Step 3: Implement the model**

```python
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, LargeBinary, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Praise(Base):
    __tablename__ = "praises"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    body_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_praises_user_id_local_date", "user_id", "local_date"),
    )
```

- [ ] **Step 4: Run the tests and observe GREEN**

Run: `cd backend && python -m pytest tests/test_praise_model.py -q`
Expected: PASS — all model tests green.

---

### Task 2: Register the model and add the migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/migrations/versions/20260901_0002_create_praises.py`
- Test: `backend/tests/test_praise_migration.py`

- [ ] **Step 1: Register Praise in the metadata aggregator**

```python
from app.core.db import Base
from app.modules.praises.models import Praise
from app.modules.users.models import User

__all__ = ["Base", "Praise", "User"]
```

- [ ] **Step 2: Write the DB-guarded schema contract test**

```python
import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Date, LargeBinary, inspect
from sqlalchemy.ext.asyncio import create_async_engine

from tests.migration_safety import require_test_database_url

RUN_DATABASE_TESTS = os.getenv("RUN_DATABASE_TESTS") == "1"


async def assert_praises_schema_contract(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            columns = await connection.run_sync(
                lambda sync: inspect(sync).get_columns("praises")
            )
            by_name = {column["name"]: column for column in columns}
            assert set(by_name) == {
                "id",
                "user_id",
                "body_ciphertext",
                "iv",
                "local_date",
                "created_at",
                "updated_at",
            }
            assert isinstance(by_name["body_ciphertext"]["type"], LargeBinary)
            assert isinstance(by_name["iv"]["type"], LargeBinary)
            assert isinstance(by_name["local_date"]["type"], Date)
            assert by_name["local_date"]["nullable"] is False

            indexes = await connection.run_sync(
                lambda sync: inspect(sync).get_indexes("praises")
            )
            assert any(
                index["column_names"] == ["user_id", "local_date"] for index in indexes
            )

            foreign_keys = await connection.run_sync(
                lambda sync: inspect(sync).get_foreign_keys("praises")
            )
            assert foreign_keys[0]["referred_table"] == "users"
    finally:
        await engine.dispose()


async def assert_praises_table_absent(database_url: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            has_table = await connection.run_sync(
                lambda sync: inspect(sync).has_table("praises")
            )
            assert has_table is False
    finally:
        await engine.dispose()


@pytest.mark.skipif(
    not RUN_DATABASE_TESTS,
    reason="set RUN_DATABASE_TESTS=1 with an isolated PostgreSQL database",
)
def test_clean_database_upgrades_to_praises_schema() -> None:
    database_url = require_test_database_url(os.environ)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.downgrade(config, "base")
    try:
        command.upgrade(config, "head")
        asyncio.run(assert_praises_schema_contract(database_url))

        command.downgrade(config, "20260831_0001")
        asyncio.run(assert_praises_table_absent(database_url))
    finally:
        command.upgrade(config, "head")
```

- [ ] **Step 3: Run the test (skips locally without PostgreSQL)**

Run: `cd backend && python -m pytest tests/test_praise_migration.py -q`
Expected: 1 skipped (no `RUN_DATABASE_TESTS`).

- [ ] **Step 4: Write the migration**

```python
"""Create the encrypted praises table.

Revision ID: 20260901_0002
Revises: 20260831_0001
Create Date: 2026-09-01 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0002"
down_revision: str | Sequence[str] | None = "20260831_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "praises",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("body_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("iv", sa.LargeBinary(), nullable=False),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_praises_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_praises")),
    )
    op.create_index(
        "ix_praises_user_id_local_date",
        "praises",
        ["user_id", "local_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_praises_user_id_local_date", table_name="praises")
    op.drop_table("praises")
```

- [ ] **Step 5: Verify Alembic sees a single linear head and no pending autogenerate diff**

Run: `cd backend && python -m alembic -c alembic.ini heads`
Expected: exactly one head, `20260901_0002`.

---

### Task 3: Full backend verification

- [ ] **Step 1: Lint**

Run: `cd backend && python -m ruff check .`
Expected: All checks passed.

- [ ] **Step 2: Test suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass; DB-dependent tests skip.

---

## Acceptance Criteria Mapping

- `body_ciphertext BYTEA`, `iv BYTEA` → `LargeBinary` columns (Task 1) + migration (Task 2).
- server-owned `local_date` → `Date` non-null, no default (Task 1 `test_local_date_is_server_owned_required_date`).
- timestamps → `created_at`/`updated_at` (Task 1).
- index `(user_id, local_date)` → `ix_praises_user_id_local_date` (Tasks 1-2).
- plaintext column absent → `test_praise_persists_only_ciphertext_and_never_plaintext` (Task 1).
