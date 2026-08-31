# Calendar API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** `GET /api/v1/calendar?from=&to=` returns the authenticated user's distinct marked days with counts over a bounded range — no ciphertext.

**Architecture:** A `from`/`to` date range (both required, bounded to ≤ 366 days) drives a grouped query `SELECT local_date, count(*) ... WHERE user_id = ? AND local_date BETWEEN ? AND ? GROUP BY local_date`, which rides the `(user_id, local_date)` index. A day with several praises collapses to one row. `loadCalendar` (frontend) fetches once and returns `{ localDate, count }[]`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, React 19, Vitest.

**Spec:** `docs/backlog.md` — `PH-302`; product-brief invariant 8.

---

### Task 1: Schema + repository + service + route (backend)
- `CalendarDay {local_date, count}` and `MAX_CALENDAR_SPAN_DAYS = 366` in `schemas.py`.
- `repository.count_praises_by_day(user_id, start, end)` grouped query.
- `service.list_calendar(telegram_id, start, end)` (UserNotFound on missing user).
- `app/api/v1/calendar.py`: required `from`/`to`, reject `to < from` or span > 366 → `422`, map UserNotFound → `401`, no ciphertext in response. Register under `/api/v1`.
- Tests: missing auth → `401`; missing/invalid params → `422`; inverted/oversized range → `422`; DB-guarded: a day with 3 praises appears once with count 3, only the caller's rows.

### Task 2: Frontend `loadCalendar`
- `frontend/src/lib/calendar.ts` + test: single authorized `GET`, returns typed days, generic error on `!ok`.

### Task 3: Verification
- Backend `ruff` + `pytest`; frontend `npm run check`.

---

## Acceptance Criteria Mapping
- bounded from/to → required params + span check (Task 1).
- only distinct dates and count, no ciphertext → `CalendarDay` grouped query (Task 1).
- query uses the index → `(user_id, local_date)` composite index + `WHERE user_id` / `GROUP BY local_date` (Task 1, by design).
- multi-entry month counts one marked day → `GROUP BY local_date` (Task 1 + DB test).
