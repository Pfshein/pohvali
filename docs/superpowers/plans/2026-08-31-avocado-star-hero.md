# Avocado Star Hero Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace cookie visuals with stars and make a full-body avocado plus a monthly star arc the primary top-of-screen composition.

**Architecture:** Keep the existing React/Vite shell and product guardrails. Extract month progress into a pure tested helper, render the decorative arc as accessible React markup, and use a transparent project-local mascot asset generated specifically for this surface.

**Tech Stack:** React 19, TypeScript, CSS, Vitest, ImageGen, Browser/IAB.

**Spec:** `docs/product-brief.md` plus the user direction from 31.08.2026.

## Global Constraints

- Stars replace cookies as the currency label and icon.
- The arc represents days praised in the current month, not a consecutive streak that can be lost.
- No pressure, missed-day, ranking, or streak-loss wording.
- Preserve the calendar, composer, encryption note, palette, and primary flow.
- Respect `prefers-reduced-motion`.

---

### Task 1: Monthly star progress model

**Files:**
- Create: `frontend/src/lib/month-progress.ts`
- Test: `frontend/src/lib/month-progress.test.ts`
- Test: `frontend/src/App.test.ts`

**Interfaces:**
- Produces: `buildMonthStarArc(praisedDays: ReadonlySet<number>, daysInMonth: number): ArcStar[]`

- [x] **Step 1: Write a failing test** proving praised days fill a stable arc without implying consecutiveness.
- [x] **Step 2: Run** the focused tests and confirm the scattered-day assertions fail first.
- [x] **Step 3: Implement** a pure clamped 28–31 day arc mapper with `filled`, `day`, and layout fields.
- [x] **Step 4: Run the focused tests** and confirm they pass.

### Task 2: Full-body avocado asset and hero

**Files:**
- Create: `frontend/src/assets/avocado-mascot.png`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `buildMonthStarProgress(...)` from Task 1.
- Produces: the `StarArc` and avocado hero composition used by the home screen.

- [x] **Step 1: Generate** a cozy full-body avocado with arms, legs, and a smile.
- [x] **Step 2: Inspect, isolate, resize, and copy** the transparent optimized asset into the project.
- [x] **Step 3: Replace** the cookie badge with a star balance and replace the raccoon card with the avocado/arc hero.
- [x] **Step 4: Keep** all existing calendar and composer behavior intact.

### Task 3: Rendered verification

**Files:**
- Modify only if QA reveals a concrete defect.

- [x] **Step 1: Run** `npm run check` in `frontend/`.
- [x] **Step 2: Rebuild** the frontend container and reload `http://localhost/`.
- [x] **Step 3: Check** 390×844 and desktop viewports, console health, asset loading, arc layout, and overflow.
- [x] **Step 4: Exercise** `Написать → valid praise → Сохранить похвалу`.
- [x] **Step 5: Compare** asset/concept and browser screenshots with `view_image`, then record the fidelity ledger in the handoff.
