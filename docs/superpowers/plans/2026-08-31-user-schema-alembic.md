# User Schema and Alembic Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the minimal privacy-preserving `users` schema and an Alembic baseline that upgrades a clean PostgreSQL database to `head`.

**Architecture:** Keep shared SQLAlchemy metadata in `app/core/db.py`, the user mapping inside the `users` domain module, and migration runtime files under `app/migrations`. Test the privacy/uniqueness contract at the ORM metadata boundary and test the migration against an ephemeral PostgreSQL 17 database.

**Tech Stack:** Python 3.12, SQLAlchemy 2 async, asyncpg, Alembic, PostgreSQL 17, Pytest, Docker Compose, GitHub Actions.

**Spec:** `docs/backlog.md` — `PH-102 · P0 · User schema и Alembic baseline`; `docs/product-brief.md` invariants 3 and 7.

## Global Constraints

- Store only `id`, `telegram_id`, `timezone`, and `created_at` in the baseline `users` table.
- Do not persist Telegram name, username, avatar, language, request body, or client IP.
- `telegram_id` is `BIGINT`, non-null, and unique.
- `timezone` is non-null and defaults to `UTC` in PostgreSQL and the ORM.
- Use UUID primary keys and timezone-aware timestamps.
- The migration must upgrade an empty PostgreSQL database to `head`, be repeatable at `head`, and downgrade to `base` for isolated test cleanup.
- Do not add session endpoints, repositories, star balances, reminders, mascots, praises, or auth tokens in this task.

---

### Task 1: Minimal users ORM contract

**Files:**
- Create: `backend/app/core/db.py`
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/users/__init__.py`
- Create: `backend/app/modules/users/models.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/test_user_model.py`

**Interfaces:**
- Produces: `app.core.db.Base` and `app.modules.users.models.User`.
- `User` maps `id: UUID`, `telegram_id: int`, `timezone: str`, and `created_at: datetime`.

- [x] **Step 1: Write the failing model contract test**

The test imports `User`, asserts that forbidden Telegram PII columns are absent, `telegram_id` is a unique non-null `BIGINT`, and `timezone` has both Python and server defaults.

- [x] **Step 2: Run the focused test and observe RED**

Run `pytest tests/test_user_model.py -q` in the backend test image. Expected failure: `ModuleNotFoundError: app.modules`.

- [x] **Step 3: Implement the shared base and user mapping**

Use SQLAlchemy 2 `DeclarativeBase`, a deterministic constraint naming convention, `sa.Uuid`, `sa.BigInteger`, `sa.String(64)`, and server defaults `gen_random_uuid()`, `'UTC'`, and `now()`.

- [x] **Step 4: Run the focused test and observe GREEN**

Run `pytest tests/test_user_model.py -q`. Expected: all model contract tests pass.

### Task 2: Alembic baseline and real PostgreSQL verification

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/app/migrations/__init__.py`
- Create: `backend/app/migrations/env.py`
- Create: `backend/app/migrations/script.py.mako`
- Create: `backend/app/migrations/versions/__init__.py`
- Create: `backend/app/migrations/versions/20260831_0001_create_users.py`
- Create: `backend/tests/test_migrations.py`
- Modify: `backend/Dockerfile`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `app.models.Base` and `Settings.database_url`.
- Produces: `alembic upgrade head`, revision `20260831_0001`, and the PostgreSQL `users` table.

- [x] **Step 1: Write the failing migration integration test**

When `RUN_DATABASE_TESTS=1`, downgrade the isolated test database to `base`, upgrade to `head` twice, insert a user without timezone, assert the stored timezone is `UTC`, and assert a duplicate `telegram_id` raises `IntegrityError`.

- [x] **Step 2: Run against ephemeral PostgreSQL and observe RED**

Start a disposable PostgreSQL 17 container and execute the focused migration test with its `DATABASE_URL`. Expected failure: missing `backend/alembic.ini` or migration environment.

- [x] **Step 3: Implement the async Alembic environment and baseline revision**

Use Alembic's async pattern with `create_async_engine`, `connection.run_sync`, and `pool.NullPool`. The revision creates exactly the four allowed columns and named PK/unique constraints; downgrade drops `users`.

- [x] **Step 4: Include migrations in backend images and CI**

Copy `alembic.ini` into the backend image. Add an ephemeral PostgreSQL 17 service and test-only `DATABASE_URL`/`RUN_DATABASE_TESTS=1` to the Backend CI job; keep credentials non-production and local to CI.

- [x] **Step 5: Document migration commands**

Add `docker compose run --rm backend alembic upgrade head` to README and state that migrations run before starting the new backend during deployment.

- [x] **Step 6: Run full verification**

Run Ruff and Pytest with migration tests against disposable PostgreSQL, `alembic current`, `alembic check`, frontend `npm run check`, `actionlint`, and `docker compose config`. Expected: every command exits `0`; the migration test executes rather than skips.

- [x] **Step 7: Review privacy and migration safety**

Confirm the database contains no forbidden Telegram PII columns, the downgrade affects only `users`, application code never calls `Base.metadata.create_all()`, and the backend still treats future praise ciphertext as out of scope.
