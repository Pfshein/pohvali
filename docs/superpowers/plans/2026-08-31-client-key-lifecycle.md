# Client Key Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every device one persistent, extractable AES-256-GCM praise key that is created on first run, reused on later runs, never sent over the network, and whose storage failures surface a calm on-device recovery screen.

**Architecture:** A pure `loadOrCreateEncryptionKey` function drives the lifecycle over an injectable `KeyStorage` port (get/set of a base64 string); the existing Telegram CloudStorage/localStorage helpers become the production adapter. A pure `createAppBootstrap` orchestrator runs session-open then key-ensure and reports four phases (`loading`, `ready`, `session-error`, `storage-error`). `SessionRoot` renders a phase-driven screen so a storage failure gets its own recovery copy distinct from a connection failure.

**Tech Stack:** TypeScript, React 19, Web Crypto (`crypto.subtle`), Vitest (node environment, `renderToStaticMarkup` for components).

**Spec:** `docs/backlog.md` — `PH-201 · P0 · Client key lifecycle`; `docs/product-brief.md` invariants 4 and 5; `AGENTS.md` (encryption on the client only).

---

## Global Constraints

- The key is `AES-256-GCM`, `extractable: true`, usages `["encrypt","decrypt"]` (already in `crypto.ts`).
- First run generates + persists once; every later run imports the same stored key (idempotent — no second write when a key already exists).
- The key and its exported material MUST never be passed to `fetch`/network. The lifecycle module imports nothing that performs network I/O.
- Any storage get/set/import failure raises `KeyStorageError`; the UI maps it to a recovery screen with a retry, never a crash or a red validation error.
- Do not implement recovery-phrase export/import here — that is `PH-202` (separate plan).
- Tests are `*.test.ts` under `frontend/src`; component assertions use `renderToStaticMarkup`.
- Do not commit (repository has no commits yet and the user has not requested commits); stop at green verification.

## File Structure

- Create `frontend/src/lib/encryption-key.ts` — `KeyStorage` port, `KeyStorageError`, `loadOrCreateEncryptionKey`, `telegramKeyStorage` adapter.
- Create `frontend/src/lib/encryption-key.test.ts` — lifecycle, idempotency, no-network, storage-error tests.
- Create `frontend/src/lib/bootstrap.ts` — `AppPhase` type and `createAppBootstrap` orchestrator.
- Create `frontend/src/lib/bootstrap.test.ts` — four-phase orchestration tests.
- Modify `frontend/src/lib/session.ts` — remove the now-superseded `createSessionBootstrap`/`SessionState` (moved into `bootstrap.ts`); keep `openSession` transport untouched.
- Modify `frontend/src/lib/session.test.ts` — drop the bootstrap describe block (moved to `bootstrap.test.ts`); keep transport tests.
- Modify `frontend/src/SessionRoot.tsx` — extract a `BootstrapScreen` component driven by `AppPhase`; wire session-open + key-ensure through `createAppBootstrap`.
- Create `frontend/src/SessionRoot.test.ts` — static-markup assertions for the loading, session-error, and storage-error screens.

---

### Task 1: Encryption key lifecycle core

**Files:**
- Create: `frontend/src/lib/encryption-key.ts`
- Test: `frontend/src/lib/encryption-key.test.ts`

**Interfaces:**
- Produces: `interface KeyStorage { getKey(): Promise<string | null>; setKey(value: string): Promise<void>; }`
- Produces: `class KeyStorageError extends Error`
- Produces: `loadOrCreateEncryptionKey(storage: KeyStorage): Promise<CryptoKey>`
- Produces: `telegramKeyStorage(): KeyStorage`

- [ ] **Step 1: Write the failing lifecycle tests**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { decryptPraise, encryptPraise } from "./crypto";
import { KeyStorageError, loadOrCreateEncryptionKey, type KeyStorage } from "./encryption-key";

function memoryStorage(initial: string | null = null): KeyStorage & { value: string | null; writes: number } {
  return {
    value: initial,
    writes: 0,
    async getKey() {
      return this.value;
    },
    async setKey(value: string) {
      this.writes += 1;
      this.value = value;
    },
  };
}

describe("encryption key lifecycle", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("generates and persists a usable key on first run", async () => {
    const storage = memoryStorage();

    const key = await loadOrCreateEncryptionKey(storage);
    const encrypted = await encryptPraise("привет", key);

    expect(storage.value).not.toBeNull();
    expect(storage.writes).toBe(1);
    await expect(decryptPraise(encrypted, key)).resolves.toBe("привет");
  });

  it("reuses the stored key without writing again", async () => {
    const first = memoryStorage();
    const key = await loadOrCreateEncryptionKey(first);
    const encrypted = await encryptPraise("одно и то же", key);

    const second = memoryStorage(first.value);
    const reused = await loadOrCreateEncryptionKey(second);

    expect(second.writes).toBe(0);
    await expect(decryptPraise(encrypted, reused)).resolves.toBe("одно и то же");
  });

  it("never touches the network", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    await loadOrCreateEncryptionKey(memoryStorage());

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("wraps a read failure in KeyStorageError", async () => {
    const storage: KeyStorage = {
      getKey: async () => { throw new Error("cloud storage offline"); },
      setKey: async () => {},
    };

    await expect(loadOrCreateEncryptionKey(storage)).rejects.toBeInstanceOf(KeyStorageError);
  });

  it("wraps a write failure in KeyStorageError", async () => {
    const storage: KeyStorage = {
      getKey: async () => null,
      setKey: async () => { throw new Error("quota exceeded"); },
    };

    await expect(loadOrCreateEncryptionKey(storage)).rejects.toBeInstanceOf(KeyStorageError);
  });

  it("wraps a corrupt stored value in KeyStorageError", async () => {
    await expect(
      loadOrCreateEncryptionKey(memoryStorage("not-a-real-key")),
    ).rejects.toBeInstanceOf(KeyStorageError);
  });
});
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `cd frontend && npx vitest run src/lib/encryption-key.test.ts`
Expected: FAIL — cannot resolve `./encryption-key`.

- [ ] **Step 3: Implement the lifecycle**

```ts
import { exportEncryptionKey, generateEncryptionKey, importEncryptionKey } from "./crypto";
import { getStoredEncryptionKey, storeEncryptionKey } from "./telegram";

export interface KeyStorage {
  getKey(): Promise<string | null>;
  setKey(value: string): Promise<void>;
}

export class KeyStorageError extends Error {
  constructor(cause?: unknown) {
    super("On-device secure storage is unavailable");
    this.name = "KeyStorageError";
    this.cause = cause;
  }
}

export async function loadOrCreateEncryptionKey(storage: KeyStorage): Promise<CryptoKey> {
  let stored: string | null;
  try {
    stored = await storage.getKey();
  } catch (error) {
    throw new KeyStorageError(error);
  }

  if (stored !== null && stored !== "") {
    try {
      return await importEncryptionKey(stored);
    } catch (error) {
      throw new KeyStorageError(error);
    }
  }

  const key = await generateEncryptionKey();
  try {
    await storage.setKey(await exportEncryptionKey(key));
  } catch (error) {
    throw new KeyStorageError(error);
  }
  return key;
}

export function telegramKeyStorage(): KeyStorage {
  return {
    getKey: () => getStoredEncryptionKey(),
    setKey: (value) => storeEncryptionKey(value),
  };
}
```

- [ ] **Step 4: Run the tests and observe GREEN**

Run: `cd frontend && npx vitest run src/lib/encryption-key.test.ts`
Expected: PASS — all six tests green.

---

### Task 2: App bootstrap orchestration with distinct error phases

**Files:**
- Create: `frontend/src/lib/bootstrap.ts`
- Create: `frontend/src/lib/bootstrap.test.ts`
- Modify: `frontend/src/lib/session.ts` (remove `createSessionBootstrap` + `SessionState`)
- Modify: `frontend/src/lib/session.test.ts` (remove the "session bootstrap" describe block)

**Interfaces:**
- Produces: `type AppPhase = "loading" | "ready" | "session-error" | "storage-error"`
- Produces: `createAppBootstrap(steps, onPhase) -> { connect: () => Promise<void> }`

- [ ] **Step 1: Write the failing orchestration tests**

```ts
import { describe, expect, it, vi } from "vitest";

import { createAppBootstrap } from "./bootstrap";

describe("app bootstrap", () => {
  it("reaches ready when session and key both succeed", async () => {
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      { openSession: vi.fn(async () => {}), ensureKey: vi.fn(async () => {}) },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "ready"]);
  });

  it("stops at session-error and never runs the key step", async () => {
    const ensureKey = vi.fn(async () => {});
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      { openSession: vi.fn(async () => { throw new Error("offline"); }), ensureKey },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "session-error"]);
    expect(ensureKey).not.toHaveBeenCalled();
  });

  it("reports storage-error when the key step throws", async () => {
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      {
        openSession: vi.fn(async () => {}),
        ensureKey: vi.fn(async () => { throw new Error("no cloud storage"); }),
      },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "storage-error"]);
  });

  it("recovers on a later retry", async () => {
    const openSession = vi.fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(undefined);
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      { openSession, ensureKey: vi.fn(async () => {}) },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();
    await bootstrap.connect();

    expect(phases).toEqual(["loading", "session-error", "loading", "ready"]);
  });
});
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `cd frontend && npx vitest run src/lib/bootstrap.test.ts`
Expected: FAIL — cannot resolve `./bootstrap`.

- [ ] **Step 3: Implement the orchestrator and move code out of session.ts**

Create `frontend/src/lib/bootstrap.ts`:

```ts
export type AppPhase = "loading" | "ready" | "session-error" | "storage-error";

interface AppBootstrapSteps {
  openSession: () => Promise<unknown>;
  ensureKey: () => Promise<unknown>;
}

export function createAppBootstrap(
  steps: AppBootstrapSteps,
  onPhase: (phase: AppPhase) => void,
): { connect: () => Promise<void> } {
  return {
    async connect() {
      onPhase("loading");
      try {
        await steps.openSession();
      } catch {
        onPhase("session-error");
        return;
      }
      try {
        await steps.ensureKey();
      } catch {
        onPhase("storage-error");
        return;
      }
      onPhase("ready");
    },
  };
}
```

In `frontend/src/lib/session.ts`, delete the `SessionState` type and the entire `createSessionBootstrap` function (lines 5 and 38-53), leaving only the `openSession` transport and its imports/`Fetcher` type.

In `frontend/src/lib/session.test.ts`, delete the `import { createSessionBootstrap }` reference (keep `openSession`) and remove the whole `describe("session bootstrap", ...)` block.

- [ ] **Step 4: Run the affected tests and observe GREEN**

Run: `cd frontend && npx vitest run src/lib/bootstrap.test.ts src/lib/session.test.ts`
Expected: PASS — orchestration tests green, transport tests still green.

---

### Task 3: SessionRoot recovery screen and full verification

**Files:**
- Modify: `frontend/src/SessionRoot.tsx`
- Create: `frontend/src/SessionRoot.test.ts`

**Interfaces:**
- Produces: `BootstrapScreen({ phase, onRetry }: { phase: AppPhase; onRetry: () => void })` rendering the loading / session-error / storage-error screens.
- `SessionRoot` wires `openSession(client)` and `loadOrCreateEncryptionKey(telegramKeyStorage())` into `createAppBootstrap`.

- [ ] **Step 1: Write the failing screen tests**

```ts
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BootstrapScreen } from "./SessionRoot";

function markup(phase: "loading" | "session-error" | "storage-error"): string {
  return renderToStaticMarkup(createElement(BootstrapScreen, { phase, onRetry: () => {} }));
}

describe("bootstrap screens", () => {
  it("shows a calm loading screen", () => {
    expect(markup("loading")).toContain("Открываем тихое место");
  });

  it("offers retry when the session fails", () => {
    const html = markup("session-error");
    expect(html).toContain("Не получилось открыть приложение");
    expect(html).toContain("Попробовать снова");
  });

  it("explains on-device storage failure with its own copy and retry", () => {
    const html = markup("storage-error");
    expect(html).toContain("на этом устройстве");
    expect(html).toContain("Попробовать снова");
    expect(html).not.toContain("Не получилось открыть приложение");
  });
});
```

- [ ] **Step 2: Run the tests and observe RED**

Run: `cd frontend && npx vitest run src/SessionRoot.test.ts`
Expected: FAIL — `BootstrapScreen` is not exported.

- [ ] **Step 3: Extract `BootstrapScreen` and wire the key phase**

Replace `frontend/src/SessionRoot.tsx` with:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";

import { App } from "./App";
import { createAppBootstrap, type AppPhase } from "./lib/bootstrap";
import { loadOrCreateEncryptionKey, telegramKeyStorage } from "./lib/encryption-key";
import { openSession } from "./lib/session";
import type { TelegramClient } from "./lib/telegram";

interface SessionRootProps {
  client: TelegramClient;
}

export function BootstrapScreen({
  phase,
  onRetry,
}: {
  phase: Exclude<AppPhase, "ready">;
  onRetry: () => void;
}) {
  return (
    <main className="session-screen">
      <section className="session-card" aria-live="polite">
        <span className="session-card__star" aria-hidden="true">★</span>
        {phase === "loading" && (
          <>
            <p className="eyebrow">Ещё мгновение</p>
            <h1>Открываем тихое место…</h1>
          </>
        )}
        {phase === "session-error" && (
          <>
            <p className="eyebrow">Связь прервалась</p>
            <h1>Не получилось открыть приложение</h1>
            <p>Можно спокойно попробовать ещё раз.</p>
            <button className="primary-button" onClick={onRetry}>Попробовать снова</button>
          </>
        )}
        {phase === "storage-error" && (
          <>
            <p className="eyebrow">Хранилище на паузе</p>
            <h1>Не удалось подготовить ключ на этом устройстве</h1>
            <p>Ключ шифрования хранится только здесь. Попробуем ещё раз?</p>
            <button className="primary-button" onClick={onRetry}>Попробовать снова</button>
          </>
        )}
      </section>
    </main>
  );
}

export function SessionRoot({ client }: SessionRootProps) {
  const [phase, setPhase] = useState<AppPhase>("loading");
  const started = useRef(false);
  const bootstrap = useMemo(
    () => createAppBootstrap(
      {
        openSession: () => openSession(client),
        ensureKey: () => loadOrCreateEncryptionKey(telegramKeyStorage()),
      },
      setPhase,
    ),
    [client],
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void bootstrap.connect();
  }, [bootstrap]);

  if (phase === "ready") return <App firstName={client.getFirstName()} />;

  return <BootstrapScreen phase={phase} onRetry={() => void bootstrap.connect()} />;
}
```

- [ ] **Step 4: Run the screen tests and observe GREEN**

Run: `cd frontend && npx vitest run src/SessionRoot.test.ts`
Expected: PASS — all three screen tests green.

- [ ] **Step 5: Full frontend verification**

Run: `cd frontend && npm run check`
Expected: lint, typecheck, the whole vitest suite, and the production build all pass.

---

## Acceptance Criteria Mapping

- extractable AES-256-GCM key → `generateEncryptionKey` (existing) driven by Task 1.
- storage adapter get/set → `KeyStorage` port + `telegramKeyStorage` (Task 1).
- second run reuses the same key → "reuses the stored key without writing again" test (Task 1).
- storage errors → recovery screen → `KeyStorageError` → `storage-error` phase → `BootstrapScreen` (Tasks 1-3).
- key never in network calls → "never touches the network" test + module has no network import (Task 1).
