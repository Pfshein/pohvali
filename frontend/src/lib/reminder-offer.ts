import type { OnboardingStorage } from "./onboarding";

const LOCAL_OFFER_KEY = "pohvala.reminder_offer.answered";

/** True when the Mini App was opened from a reminder push button. */
export function enteredFromReminder(search: string): boolean {
  return new URLSearchParams(search).get("from") === "reminder";
}

/** The one-time offer is for direct entry only and never repeats after an answer. */
export function shouldShowReminderOffer(input: {
  fromReminder: boolean;
  answered: boolean;
}): boolean {
  return !input.fromReminder && !input.answered;
}

export async function loadReminderOfferAnswered(storage: OnboardingStorage): Promise<boolean> {
  try {
    return (await storage.get()) !== null;
  } catch {
    // Broken storage must not crash the app; treat as unanswered.
    return false;
  }
}

export async function markReminderOfferAnswered(storage: OnboardingStorage): Promise<void> {
  await storage.set("answered");
}

export function telegramReminderOfferStorage(): OnboardingStorage {
  // Same CloudStorage-with-local-fallback shape as the onboarding flag.
  const cloud = window.Telegram?.WebApp.CloudStorage;

  return {
    get: async () => {
      if (cloud) {
        try {
          const value = await new Promise<string | null>((resolve, reject) => {
            cloud.getItem("reminder_offer_answered", (error, value) => {
              if (error) reject(error);
              else resolve(value || null);
            });
          });
          if (value) return value;
        } catch {
          // Fall back to device-local storage when CloudStorage is unsupported.
        }
      }
      return localStorage.getItem(LOCAL_OFFER_KEY);
    },
    set: async (value) => {
      if (cloud) {
        try {
          await new Promise<void>((resolve, reject) => {
            cloud.setItem("reminder_offer_answered", value, (error, stored) => {
              if (error) reject(error);
              else if (stored === false) reject(new Error("CloudStorage declined the write"));
              else resolve();
            });
          });
          return;
        } catch {
          // Fall back to device-local storage when CloudStorage is unsupported.
        }
      }
      localStorage.setItem(LOCAL_OFFER_KEY, value);
    },
  };
}
