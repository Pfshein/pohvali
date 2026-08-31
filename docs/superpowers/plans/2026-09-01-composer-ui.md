# Composer Save Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the composer to a real save: encrypt on-device, POST once, and show a success state that does not hold the user.

**Architecture:** `savePraise(client, key, text, fetcher)` (lib) encrypts the trimmed text with the device key and does a single authorized `POST /api/v1/praises`, returning the parsed `PraiseCreated`. `SessionRoot` keeps the ensured key in state and passes an `onSubmitPraise` closure to `App`. `App`'s composer stays disabled (calmly, no red error) until `isValidPraise`, calls `onSubmitPraise` once, and clears to a brief success toast; failures show a gentle retry message.

**Tech Stack:** React 19, Web Crypto, Vitest.

**Spec:** `docs/backlog.md` — `PH-205`; product-brief invariants 2, 4.

---

### Task 1: `savePraise` transport (DONE via TDD)

**Files:** `frontend/src/lib/praise-api.ts`, `frontend/src/lib/praise-api.test.ts`
- Encrypts trimmed text, one `POST /api/v1/praises` with `Authorization: tma <initData>`, body `{body_ciphertext, iv}`; validates the response shape; throws a generic `Could not save praise` on `!ok` without leaking the body.
- Tests: single round-trip + ciphertext excludes plaintext; generic error on failure.

### Task 2: Wire key + composer (DONE)

**Files:** `frontend/src/SessionRoot.tsx`, `frontend/src/App.tsx`
- `SessionRoot` stores the ensured `CryptoKey` in state and passes `onSubmitPraise={key ? (text) => savePraise(client, key, text) : undefined}`.
- `App` gains optional `onSubmitPraise`; `handleSave` awaits it with an `isSaving` guard (button shows «Сохраняем…», disabled while saving or invalid), success clears the composer to a short toast, failure shows a calm retry message. Without the prop, the local prototype message is kept (used by the hero render test).

### Task 3: Verification (DONE)

- `cd frontend && npm run check` → lint, typecheck, 40 tests, build all green.

---

## Acceptance Criteria Mapping

- trim 4–500 + Unicode letter → `isValidPraise` gates `canSave`.
- calmly disabled until valid → `disabled={!canSave || isSaving}`, no red error.
- one API round-trip → `savePraise` single `fetcher` call (tested).
- success-state does not hold the user → composer closes + auto-dismissing toast.
