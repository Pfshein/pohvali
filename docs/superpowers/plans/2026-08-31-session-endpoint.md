# Telegram Session Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a privacy-preserving `POST /api/v1/session` endpoint that authenticates Telegram Mini App data and idempotently creates or updates the minimal user profile.

**Architecture:** A FastAPI authentication dependency validates the `Authorization: tma <initDataRaw>` header and exposes only `TelegramIdentity`. The users module owns timezone validation, PostgreSQL upsert, and transaction boundaries; the API router only maps validated input and output. The response contains only the internal UUID and canonical timezone.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2 async, asyncpg, PostgreSQL 17, Pytest, HTTPX.

**Spec:** `docs/backlog.md` — `PH-103 · P0 · POST /api/v1/session`; `docs/product-brief.md` sections 6, 8.1, 9, 12, 13, and 16.

## Global Constraints

- Authenticate every request with fresh Telegram `initData`; do not add JWT or another token.
- Accept only `Authorization: tma <initDataRaw>` and return `401` without echoing header contents when it is absent, malformed, tampered, or expired.
- Extract and use only integer Telegram `id`; never persist or return name, username, avatar, or language.
- Validate `timezone` against the installed IANA timezone database and accept `UTC` as the safe fallback.
- Upsert by unique `telegram_id`; every successful opening updates the saved timezone and never creates a duplicate user.
- Keep the transaction boundary in the users service, not the API router.
- Return only `{id, timezone}` until later profile fields have their own schemas and migrations.
- Do not log authorization headers, request bodies, Telegram IDs, or Telegram user payloads.

---

### Task 1: Authentication and database dependencies

**Files:**
- Modify: `backend/app/core/db.py`
- Create: `backend/app/api/dependencies.py`
- Test: `backend/tests/test_api_dependencies.py`

**Interfaces:**
- Produces: `get_db_session() -> AsyncIterator[AsyncSession]`.
- Produces: `get_telegram_identity(authorization, settings) -> TelegramIdentity`.

- [x] **Step 1: Write failing dependency tests**

Test a valid signed header, a missing header, a wrong scheme, and tampered data. Assert failures are `401` with a generic response that does not contain the raw query string.

- [x] **Step 2: Run the focused tests and observe RED**

Run `pytest tests/test_api_dependencies.py -q`. Expected: import failure because `app.api.dependencies` does not exist.

- [x] **Step 3: Implement minimal dependencies**

Create a cached async engine/session factory from `Settings.database_url`, yield sessions without committing, parse the `tma` scheme, and translate `InvalidInitData`/parse failures to a generic `401` response with `WWW-Authenticate: tma`.

- [x] **Step 4: Run the focused tests and observe GREEN**

Run `pytest tests/test_api_dependencies.py -q`. Expected: all dependency tests pass.

### Task 2: IANA timezone contract

**Files:**
- Create: `backend/app/modules/users/schemas.py`
- Test: `backend/tests/test_user_schemas.py`

**Interfaces:**
- Produces: `SessionRequest(timezone: str)` and `UserProfile(id: UUID, timezone: str)`.

- [x] **Step 1: Write failing schema tests**

Test `UTC` and `Europe/Moscow` as accepted literals; test an unknown zone, traversal-like value, blank value, and value longer than 64 characters as rejected inputs.

- [x] **Step 2: Run the focused tests and observe RED**

Run `pytest tests/test_user_schemas.py -q`. Expected: import failure because `app.modules.users.schemas` does not exist.

- [x] **Step 3: Implement the schemas**

Use a Pydantic field validator that constructs `zoneinfo.ZoneInfo(value)` and returns its key. Keep the database limit at 64 characters and configure `UserProfile` for ORM attribute parsing.

- [x] **Step 4: Run the focused tests and observe GREEN**

Run `pytest tests/test_user_schemas.py -q`. Expected: all schema tests pass.

### Task 3: Atomic idempotent session upsert

**Files:**
- Create: `backend/app/modules/users/repository.py`
- Create: `backend/app/modules/users/service.py`
- Create: `backend/app/api/v1/session.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/test_session_api.py`

**Interfaces:**
- Consumes: `TelegramIdentity.telegram_id`, `SessionRequest.timezone`, and an `AsyncSession`.
- Produces: `upsert_user(session, telegram_id, timezone) -> User` using PostgreSQL `ON CONFLICT`.
- Produces: `open_session(session, telegram_id, timezone) -> User`, owning `session.begin()`.
- Produces: `POST /api/v1/session -> UserProfile`.

- [x] **Step 1: Write the failing PostgreSQL API integration tests**

Against the isolated `_test` database, send signed requests containing extra Telegram profile fields. Assert first call creates one user, second call returns the same UUID and updates timezone, response keys are exactly `id` and `timezone`, invalid timezone creates no user, and invalid auth returns `401`.

- [x] **Step 2: Run the focused integration tests and observe RED**

Run `pytest tests/test_session_api.py -q` with `RUN_DATABASE_TESTS=1` and the isolated PostgreSQL URL. Expected: `404` for the missing route.

- [x] **Step 3: Implement repository, service, and thin route**

Use PostgreSQL `insert(User).on_conflict_do_update(index_elements=[User.telegram_id], set_={"timezone": timezone}).returning(User)`. The service wraps it in `async with session.begin()`. Register the route under the existing `/api/v1` router.

- [x] **Step 4: Run the focused integration tests and observe GREEN**

Run `pytest tests/test_session_api.py -q` against the isolated database. Expected: all session API tests pass.

### Task 4: Contract documentation and full verification

**Files:**
- Modify: `README.md`
- Create: `frontend/src/lib/api.ts`
- Modify: this plan

**Interfaces:**
- Documents: request header/body, minimal response, error behavior, and a local smoke command without real secrets.
- Produces: matching frontend `SessionRequest` and `SessionProfile` types for PH-104.

- [x] **Step 1: Document the session contract**

Add the endpoint shape and privacy boundary to README. Do not include a real bot token or signed production payload.

- [x] **Step 2: Run backend verification**

Against an isolated PostgreSQL database, run `ruff check .`, `pytest`, and `alembic check`. Confirm the database tests execute rather than skip.

- [x] **Step 3: Run repository verification**

Run frontend `npm run check`, `actionlint`, and `docker compose config --quiet`.

- [x] **Step 4: Review requirements and privacy**

Confirm the OpenAPI schema exposes `POST /api/v1/session`, the response has no Telegram PII, service owns the transaction, and no code persists or logs the authorization payload.

- [x] **Step 5: Request independent code review**

Review all PH-103 files against this plan. Fix every Critical or Important finding, then rerun the affected checks.
