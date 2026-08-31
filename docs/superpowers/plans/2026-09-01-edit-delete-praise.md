# Edit & Delete Praise Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** Owners can edit a past praise (ciphertext/iv/sticker + `updated_at`, no new star) and delete their own praise (daily star not revoked), with ownership enforced and non-existent/other-user resources indistinguishable (`404`).

**Architecture:** Add a nullable `sticker` column to `praises` (catalog validation lands in PH-401). `PATCH /api/v1/praises/{id}` and `DELETE /api/v1/praises/{id}` load the user, then run an `UPDATE ... WHERE id=? AND user_id=? RETURNING id` / `DELETE ... WHERE id=? AND user_id=?`; an empty result raises `PraiseNotFound → 404` so UUID enumeration reveals nothing. Neither path touches the star ledger or balance.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, Pytest.

**Spec:** `docs/backlog.md` — `PH-304`, `PH-305`; PH-701 (no enumeration); product-brief invariant 2 (star only for first daily entry).

---

### Task 1: `sticker` column (model + migration)
- Add `sticker: str | None` (`String(32)`, nullable) to `Praise`.
- Migration `20260901_0004` adds/drops the column.
- Update `test_praise_model.py` columns set + a sticker assertion; update `test_praise_migration.py` expected columns.

### Task 2: Edit
- `PraiseEditRequest {body_ciphertext, iv, sticker?}` (reuse base64 validators; 4 KiB cap in route → `413`).
- `repository.update_praise(user_id, praise_id, ciphertext, iv, sticker) -> bool`.
- `service.update_praise(...)` raises `PraiseNotFound` when nothing updated.
- `PATCH /api/v1/praises/{praise_id}` → `204`; `401` unauth, `413` oversized, `404` not owned. Never awards a star.
- Tests: unauth `401`, oversized `413`, invalid body `422`; DB-guarded: fields + `updated_at` change, balance unchanged, cross-user edit → `404`.

### Task 3: Delete
- `repository.delete_praise(user_id, praise_id) -> bool`.
- `service.delete_praise(...)` raises `PraiseNotFound` when nothing deleted.
- `DELETE /api/v1/praises/{praise_id}` → `204`; `401`, `404` not owned.
- Tests: unauth `401`; DB-guarded: own delete removes row and keeps balance/ledger, cross-user delete → `404`.

### Task 4: Verify
- `python -m ruff check .`, `python -m pytest -q`; DB tests skip locally.

---

## Acceptance Criteria Mapping
- edit allowed for past dates → no date restriction in `update_praise` (Task 2).
- ciphertext/iv/sticker + `updated_at` change → update statement + `onupdate=now()` (Task 2).
- star not awarded on edit → edit never calls the ledger (Task 2).
- delete only own; daily star not revoked → owner-scoped delete, ledger/balance untouched (Task 3).
- ownership required, no enumeration → owner-scoped `WHERE` + uniform `404` (Tasks 2-3).
