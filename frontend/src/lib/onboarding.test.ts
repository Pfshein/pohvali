import { afterEach, describe, expect, it, vi } from "vitest";

import {
  loadOnboarding,
  saveOnboarding,
  telegramOnboardingStorage,
  type OnboardingStorage,
} from "./onboarding";

function memoryStorage(initial: string | null = null): OnboardingStorage & { value: string | null } {
  return {
    value: initial,
    async get() {
      return this.value;
    },
    async set(value: string) {
      this.value = value;
    },
  };
}

function fakeLocalStorage() {
  const map = new Map<string, string>();
  return {
    store: map,
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
    clear: () => map.clear(),
    key: () => null,
    length: 0,
  };
}

describe("onboarding state", () => {
  it("treats empty storage as not completed", async () => {
    expect(await loadOnboarding(memoryStorage())).toEqual({ completed: false, mascot: null });
  });

  it("treats a stored mascot as completed", async () => {
    expect(await loadOnboarding(memoryStorage("ava"))).toEqual({ completed: true, mascot: "ava" });
  });

  it("persists the chosen starter mascot", async () => {
    const storage = memoryStorage();
    await saveOnboarding(storage, "ava");
    expect(storage.value).toBe("ava");
    expect((await loadOnboarding(storage)).completed).toBe(true);
  });

  it("falls back to showing onboarding when storage fails", async () => {
    const failing: OnboardingStorage = {
      get: async () => {
        throw new Error("no storage");
      },
      set: async () => {},
    };
    expect(await loadOnboarding(failing)).toEqual({ completed: false, mascot: null });
  });
});

describe("telegramOnboardingStorage", () => {
  afterEach(() => vi.unstubAllGlobals());

  // Telegram's telegram-web-app.js always defines CloudStorage, but outside a real
  // Telegram host every call errors with "CloudStorage is not supported in version 6.0".
  const brokenCloud = {
    getItem: (_key: string, cb: (error: Error | null, value?: string) => void) =>
      cb(new Error("CloudStorage is not supported in version 6.0")),
    setItem: (_key: string, _value: string, cb?: (error: Error | null) => void) =>
      cb?.(new Error("CloudStorage is not supported in version 6.0")),
  };

  it("falls back to localStorage when CloudStorage is unsupported", async () => {
    vi.stubGlobal("localStorage", fakeLocalStorage());
    vi.stubGlobal("window", { Telegram: { WebApp: { CloudStorage: brokenCloud } } });

    const storage = telegramOnboardingStorage();
    await expect(storage.set("ava")).resolves.toBeUndefined();
    expect(await storage.get()).toBe("ava");
  });

  it("uses CloudStorage when it works", async () => {
    const backing = new Map<string, string>();
    const cloud = {
      getItem: (key: string, cb: (error: Error | null, value?: string) => void) =>
        cb(null, backing.get(key)),
      setItem: (key: string, value: string, cb?: (error: Error | null) => void) => {
        backing.set(key, value);
        cb?.(null);
      },
    };
    vi.stubGlobal("localStorage", fakeLocalStorage());
    vi.stubGlobal("window", { Telegram: { WebApp: { CloudStorage: cloud } } });

    const storage = telegramOnboardingStorage();
    await storage.set("mira");
    expect(backing.get("onboarding_mascot")).toBe("mira");
    expect(await storage.get()).toBe("mira");
  });
});
