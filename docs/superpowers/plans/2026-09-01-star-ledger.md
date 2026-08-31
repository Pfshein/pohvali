# Star Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an append-only `star_ledger` and a non-negative `star_balances` store so a user earns at most one star per local day and a balance can never go below zero.

**Architecture:** Two ORM models on the shared `Base`. `star_ledger` is insert-only (no update/delete code path) with a **partial unique index** on `(user_id, local_date)` filtered to `reason = 'daily'`, guaranteeing one daily star per local day even under concurrency. `star_balances` holds a materialized per-user balance with a `CHECK (balance >= 0)` constraint (row-lockable for PH-204/PH-403). Both cascade on user delete.

**Tech Stack:** SQLAlchemy 2 async, Alembic, PostgreSQL 17, Pytest.

**Spec:** `docs/backlog.md` — `PH-301 · P0 · Star ledger`; product-brief invariant 2.

---

## Global Constraints

- `star_ledger`: `id, user_id, amount, reason, local_date, created_at`. Append-only by convention (only inserts).
- Partial unique index `uq_star_ledger_daily_per_day` on `(user_id, local_date) WHERE reason = 'daily'`.
- `star_balances`: `user_id` PK, `balance` int (default 0), `updated_at`; `CHECK (balance >= 0)`.
- Both `user_id` → `users.id`, `ON DELETE CASCADE`.
- No award/spend logic here — that is PH-204/PH-403.

---

### Task 1: Star ledger and balance models

**Files:**
- Create: `backend/app/modules/stars/__init__.py`
- Create: `backend/app/modules/stars/models.py`
- Test: `backend/tests/test_star_models.py`

- [ ] **Step 1: Write failing model tests** — assert ledger columns, the partial unique index (unique + `reason = 'daily'` predicate), balance CHECK `>= 0`, and CASCADE FKs.
- [ ] **Step 2: Run `python -m pytest tests/test_star_models.py -q` → RED** (module missing).
- [ ] **Step 3: Implement `StarLedgerEntry` and `StarBalance`.**
- [ ] **Step 4: Run tests → GREEN.**

### Task 2: Register models and migration

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/migrations/versions/20260901_0003_create_star_ledger.py`
- Test: `backend/tests/test_star_migration.py` (DB-guarded, skips locally)

- [ ] **Step 1:** Import both models in `app/models.py`, extend `__all__`.
- [ ] **Step 2:** Write DB-guarded schema contract test (columns, partial unique index, CHECK).
- [ ] **Step 3:** Write migration `20260901_0003` (down_revision `20260901_0002`).
- [ ] **Step 4:** `python -m alembic -c alembic.ini heads` → single head `20260901_0003`.

### Task 3: Verification

- [ ] `python -m ruff check .` → clean.
- [ ] `python -m pytest -q` → all pass, DB tests skip.

---

## Acceptance Criteria Mapping

- append-only ledger → `StarLedgerEntry` insert-only model (Task 1).
- partial unique index for `(user_id, local_date)` at `reason='daily'` → `uq_star_ledger_daily_per_day` (Tasks 1-2).
- balance cannot go negative → `CHECK (balance >= 0)` on `star_balances` (Tasks 1-2).
