# Create Praise + Daily Star Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `POST /api/v1/praises` stores an encrypted praise and, atomically, awards at most one daily star and bumps the balance — with the server owning the date and a 4 KiB blob cap.

**Architecture:** A thin FastAPI route validates the base64 payload, enforces the 4 KiB ciphertext cap (413), and delegates to `praises.service.create_praise`, which runs one `session.begin()` transaction: load the user (for id + timezone), insert the praise, attempt a `reason='daily'` ledger insert via `ON CONFLICT DO NOTHING` against the partial unique index, and only when that insert actually happened, upsert `star_balances += 1`. Concurrency safety comes from the DB (partial unique index + non-negative CHECK), not app locks.

**Tech Stack:** FastAPI, Pydantic 2, SQLAlchemy 2 async (PostgreSQL `INSERT ... ON CONFLICT`), Pytest.

**Spec:** `docs/backlog.md` — `PH-204`; product-brief invariants 2, 3, 4.

---

## Global Constraints

- Request body: `{ body_ciphertext: base64, iv: base64 }`. No date field; the server computes `local_date` from the user's saved IANA timezone. Extra fields (e.g. a client date) are ignored.
- `iv` decodes to exactly 12 bytes; `body_ciphertext` is non-empty; invalid base64 or wrong iv length → `422`.
- Decoded ciphertext larger than 4096 bytes → `413`.
- Praise insert + daily-star ledger + balance change happen in ONE transaction.
- Concurrent first-of-day requests award at most one star; extra same-day praises award none but still persist.
- Response: `{ id, local_date, star_awarded, balance }`.

---

### Task 1: Request/response schema

**Files:** Create `backend/app/modules/praises/schemas.py`; Test `backend/tests/test_praise_schemas.py`

- [ ] Write failing tests: valid payload exposes `ciphertext_bytes`/`iv_bytes`; invalid base64 → `ValidationError`; iv ≠ 12 bytes → `ValidationError`; empty ciphertext → `ValidationError`; an extra `local_date` key is ignored.
- [ ] RED: `python -m pytest tests/test_praise_schemas.py -q`.
- [ ] Implement `PraiseCreateRequest` (fields `body_ciphertext`, `iv`; base64 validators; `ciphertext_bytes`/`iv_bytes` properties; `extra="ignore"`), `PraiseCreated`, and constants `MAX_CIPHERTEXT_BYTES=4096`, `IV_BYTES=12`.
- [ ] GREEN.

### Task 2: Repository + transactional service

**Files:** Create `backend/app/modules/praises/repository.py`, `backend/app/modules/praises/service.py`; Test `backend/tests/test_praise_service.py`

- [ ] Write failing pure test for `local_date_in_timezone(timezone, moment)` (a `2026-09-01T00:30:00Z` moment resolves to `2026-09-01` in `Europe/Moscow` and to `2026-08-31` in `America/New_York`).
- [ ] RED.
- [ ] Implement repository (`get_user`, `insert_praise`, `try_award_daily_star` via `on_conflict_do_nothing(index_elements=["user_id","local_date"], index_where=text("reason = 'daily'"))`, `increment_balance` upsert, `get_balance`) and `service.create_praise` (one `session.begin()`, `PraiseResult` dataclass, `UserNotFound`).
- [ ] GREEN.

### Task 3: API route

**Files:** Create `backend/app/api/v1/praises.py`; Modify `backend/app/api/v1/router.py`; Test `backend/tests/test_praises_api.py`

- [ ] Write failing tests (TestClient, `get_telegram_identity` + `get_db_session` overridden): oversized ciphertext → `413` and the service is never called; missing auth → `401`.
- [ ] RED.
- [ ] Implement route: decode via schema, `len(ciphertext) > MAX_CIPHERTEXT_BYTES` → `413`, call `create_praise`, map `UserNotFound` → `401`, return `PraiseCreated` with `201`.
- [ ] Register under `/api/v1`.
- [ ] GREEN.

### Task 4: DB-guarded integration (skips locally) + frontend types + verify

**Files:** Create `backend/tests/test_praise_create_db.py`; Modify `frontend/src/lib/api.ts`

- [ ] Write DB-guarded test: first create → `201`, `star_awarded=True`, `balance=1`, praise row has server `local_date`; second same-day create → `star_awarded=False`, `balance=1`, two praise rows; two concurrent first-of-day creates → exactly one star, `balance=1`.
- [ ] Add matching `PraiseCreateRequest`/`PraiseCreated` TypeScript types to `frontend/src/lib/api.ts`.
- [ ] Verify: `python -m ruff check .`, `python -m pytest -q` (DB tests skip), `cd frontend && npm run check`.

---

## Acceptance Criteria Mapping

- one transaction → `service.create_praise` single `session.begin()` (Task 2).
- ≤ one daily star under concurrency → partial-index `ON CONFLICT DO NOTHING` (Tasks 2, 4).
- payload > 4 KiB → `413` (Tasks 1, 3).
- client date not accepted → no date field, `extra="ignore"`, server computes `local_date` (Tasks 1, 2, 4).
