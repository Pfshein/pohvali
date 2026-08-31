import { describe, expect, it } from "vitest";

import { loadOnboarding, saveOnboarding, type OnboardingStorage } from "./onboarding";

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
