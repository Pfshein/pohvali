# Mobile Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** A pageable, accessible month calendar whose grid holds any 28–31 day month and whose caption is calm («⭐ N в месяце»), with no streak wording.

**Architecture:** A pure `month-grid.ts` builds a Monday-first grid (leading/trailing blanks, marked days, `markedCount`) plus nominative/genitive month names. A presentational `MonthCalendar` renders the grid as accessible day `<button>`s (`aria-label` with genitive date, `aria-pressed` for the selected day) and prev/next controls. `App` owns `viewMonth`/`selectedDay` state and pages months via `shiftMonth` with year rollover.

**Tech Stack:** React 19, Vitest (`renderToStaticMarkup`).

**Spec:** `docs/backlog.md` — `PH-303`; product-brief invariant 1 (no streak/pressure).

---

### Task 1: `month-grid.ts` (DONE)
- `buildMonthGrid`, `daysInMonth`, `russianMonthName`, `russianMonthNameGenitive`.
- Tests: day counts for 28/29/30/31, Monday-first offset, padded weeks, marked-once counting.

### Task 2: `MonthCalendar` component (DONE)
- Accessible day buttons, calm caption, month navigation controls.
- Tests: one button per day for several month lengths, caption without streak wording, marked/selected `aria` labels, nav controls.

### Task 3: Wire into `App` + verify (DONE)
- `App` pages months (`shiftMonth`, year rollover), clears selection on page.
- `cd frontend && npm run check` → 63 tests, build.

---

## Deferred / Handoff
- **Live per-month marks.** The prototype marks only the seeded month; wire `loadCalendar`
  (`frontend/src/lib/calendar.ts`, from PH-302) per `viewMonth` to fill `markedDays` from the API.
- **Day view.** Selecting a day should open the decrypted list via `loadDay` (PH-206), rendering
  the «не удалось открыть запись» note for `unreadable` entries.

## Acceptance Criteria Mapping
- months page → `shiftMonth` + prev/next controls (Tasks 2-3).
- 28–31 days do not break the grid → `buildMonthGrid` padding (Task 1 + component test).
- selected day is keyboard/SR reachable → focusable `<button>` + `aria-pressed`/`aria-label` (Task 2).
- caption «⭐ N в месяце», no streak wording → caption test (Task 2).
