import { describe, expect, it } from "vitest";

import {
  enteredFromReminder,
  loadReminderOfferAnswered,
  markReminderOfferAnswered,
  shouldShowReminderOffer,
} from "./reminder-offer";
import type { OnboardingStorage } from "./onboarding";

function memoryStorage(): OnboardingStorage & { value: string | null } {
  const storage = { value: null as string | null };
  return {
    value: storage.value,
    async get() {
      return storage.value;
    },
    async set(next: string) {
      storage.value = next;
    },
  };
}

describe("reminder offer decision", () => {
  it("detects entry from a reminder by the url marker", () => {
    expect(enteredFromReminder("?from=reminder")).toBe(true);
    expect(enteredFromReminder("?other=1&from=reminder")).toBe(true);
    expect(enteredFromReminder("")).toBe(false);
    expect(enteredFromReminder("?from=menu")).toBe(false);
  });

  it("is shown once on direct entry and never after an answer", () => {
    expect(shouldShowReminderOffer({ fromReminder: false, answered: false })).toBe(true);
    expect(shouldShowReminderOffer({ fromReminder: true, answered: false })).toBe(false);
    expect(shouldShowReminderOffer({ fromReminder: false, answered: true })).toBe(false);
    expect(shouldShowReminderOffer({ fromReminder: true, answered: true })).toBe(false);
  });

  it("keeps the answer in storage so the offer is never repeated", async () => {
    const storage = memoryStorage();

    expect(await loadReminderOfferAnswered(storage)).toBe(false);
    await markReminderOfferAnswered(storage);
    expect(await loadReminderOfferAnswered(storage)).toBe(true);
  });

  it("treats broken storage as unanswered instead of failing", async () => {
    const broken: OnboardingStorage = {
      get: async () => {
        throw new Error("CloudStorage declined");
      },
      set: async () => {},
    };

    expect(await loadReminderOfferAnswered(broken)).toBe(false);
  });
});
