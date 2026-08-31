# Onboarding Implementation Plan (PH-601)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans.

**Goal:** A two-screen onboarding whose last step is the free starter-mascot pick, that never gates
on push permission and never shows again once completed.

**Architecture:** `onboarding.ts` is a storage port (`OnboardingStorage`) plus `loadOnboarding` /
`saveOnboarding` (a stored mascot code is the "completed" marker; storage failure ⇒ show onboarding
again, no crash) with a Telegram CloudStorage / localStorage adapter. `Onboarding` is a
presentational two-step component (intro → mascot pick). `OnboardingGate` (in `SessionRoot`) reads
completion on mount and renders either the flow or the app; finishing persists the mascot and reveals
the app. Starter list lives in `lib/mascots.ts` (replaced by the PH-401 catalog later).

**Tech Stack:** React 19, Vitest.

**Spec:** `docs/backlog.md` — `PH-601`; product-brief invariant 1.

---

### Task 1: Onboarding state (DONE)
- `onboarding.ts` + tests: empty ⇒ not completed, stored mascot ⇒ completed, persists pick, storage
  failure ⇒ not completed (graceful).

### Task 2: Onboarding component (DONE)
- `Onboarding.tsx` two steps; mascot pick last; finish disabled until a starter is chosen.
- Tests: two-screen shape, mascot pick last, no push-permission wording, finish gating.

### Task 3: Gate + wiring (DONE)
- `OnboardingGate` in `SessionRoot` reads/writes completion and wraps `App`; `npm run check` green.

---

## Acceptance Criteria Mapping
- at most two screens → `Onboarding` renders only step 0 / step 1 (test).
- starter mascot pick is last → step 1 is the mascot picker (test).
- continue without push permission → no push gate anywhere; intro advances freely (test).
- not shown again → completion persisted via `saveOnboarding`; `OnboardingGate` skips when completed.
