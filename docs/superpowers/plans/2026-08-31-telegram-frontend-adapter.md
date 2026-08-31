# Telegram Frontend Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the React shell to the trusted Telegram session endpoint while keeping ordinary local-browser development explicit and usable.

**Architecture:** A small Telegram client encapsulates the real WebApp object and an explicitly configured local mock. A separate session client sends only raw `initData` and the resolved IANA timezone to `/api/v1/session`; a tiny bootstrap state machine exposes loading, ready, error, and retry states without coupling the product screen to transport details.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Web Crypto, Vitest, Telegram Mini Apps JavaScript API.

**Spec:** `docs/backlog.md` — `PH-104 · P0 · Telegram frontend adapter`; `docs/product-brief.md` sections 8.1, 9, 12, 13, and 16.

## Global Constraints

- Production sends the untouched `window.Telegram.WebApp.initData`; never use `initDataUnsafe` for authentication.
- Call Telegram `ready()` and `expand()` during application bootstrap.
- Send `Intl.DateTimeFormat().resolvedOptions().timeZone` on every session opening; use `UTC` when lookup is empty or throws.
- Browser development uses an explicit `VITE_TELEGRAM_MODE=mock`; production defaults to `telegram`.
- The mock signs only a fixed fake user with the public local placeholder token `dev-token`; no real bot token enters frontend code or build arguments.
- The session request contains only `{timezone}` and `Authorization: tma <initDataRaw>`.
- Session failure shows a calm retry state; it does not expose credentials or Telegram payloads.
- Keep existing avocado/star visuals and praise prototype behavior unchanged.

---

### Task 1: Real Telegram and explicit browser mock adapters

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/types/telegram.d.ts`
- Create: `frontend/src/lib/dev-telegram.ts`
- Modify: `frontend/src/lib/telegram.ts`
- Create: `frontend/src/lib/telegram.test.ts`

**Interfaces:**
- Produces: `createTelegramClient(options) -> TelegramClient` with `initialize()`, `getInitData()`, `getFirstName()`, `getTimezone()`, and `mode`.
- Production client consumes `window.Telegram.WebApp`; mock client creates fresh signed data for fake integer user ID `900000001`.

- [x] **Step 1: Write failing adapter tests**

Cover untouched production `initData`, `ready()`/`expand()`, explicit mock selection, refusal outside Telegram when mock is disabled, and timezone fallback for empty/throwing Intl results.

- [x] **Step 2: Run focused tests and observe RED**

Run `npm test -- src/lib/telegram.test.ts`. Expected: missing `createTelegramClient`/mock implementation.

- [x] **Step 3: Implement the minimal adapters**

Load the official Telegram script before the app module, use Web Crypto HMAC only in mock mode, and keep `initDataUnsafe.first_name` display-only.

- [x] **Step 4: Run focused tests and observe GREEN**

Run `npm test -- src/lib/telegram.test.ts`. Expected: adapter tests pass.

### Task 2: Session transport and bootstrap states

**Files:**
- Create: `frontend/src/lib/session.ts`
- Create: `frontend/src/lib/session.test.ts`
- Create: `frontend/src/SessionRoot.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Produces: `openSession(client, fetcher) -> Promise<SessionProfile>`.
- Produces: `createSessionBootstrap(open, onState) -> { connect() }` with states `loading | ready | error`.

- [x] **Step 1: Write failing session tests**

Assert the exact URL, method, authorization header, JSON body, minimal parsed profile, generic failure, state transitions, and successful retry.

- [x] **Step 2: Run focused tests and observe RED**

Run `npm test -- src/lib/session.test.ts`. Expected: missing session module.

- [x] **Step 3: Implement transport and calm bootstrap UI**

Keep the main screen mounted only after a successful session. Render a neutral loading card, and on failure render a retry button without raw response or authorization details.

- [x] **Step 4: Run focused tests and observe GREEN**

Run `npm test -- src/lib/session.test.ts`. Expected: all session/bootstrap tests pass.

### Task 3: Environment wiring and end-to-end verification

**Files:**
- Modify: `frontend/Dockerfile`
- Modify: `compose.yaml`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: this plan

**Interfaces:**
- Produces: local Vite development with explicit mock mode and Compose/production builds defaulting to real Telegram mode.

- [x] **Step 1: Wire the build mode**

Pass `VITE_TELEGRAM_MODE` as a frontend build arg. Direct Vite development uses a committed mock-only development env; Compose and production default to `telegram` and require an explicit mock override for local browser use.

- [x] **Step 2: Run complete static verification**

Run `npm run check`, backend `ruff check .` and `pytest`, and `docker compose config --quiet`.

- [x] **Step 3: Verify production bundle privacy**

Build with `VITE_TELEGRAM_MODE=telegram` and confirm the production bundle does not contain `dev-token`, the fake user ID, or mock display data.

- [x] **Step 4: Verify the rendered target flow**

Rebuild local frontend, open `http://localhost`, verify page identity, meaningful DOM, no overlay, clean console, screenshot, and an interaction. Confirm the mock `/session` request succeeds against the real backend and creates only the fake minimal user.

- [x] **Step 5: Request code review and close findings**

Review the adapter, session transport, build-mode boundary, privacy, and tests. Fix Critical and Important findings, rerun affected checks, and mark this plan complete.
