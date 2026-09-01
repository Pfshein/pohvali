export interface OnboardingStorage {
  get(): Promise<string | null>;
  set(value: string): Promise<void>;
}

export interface OnboardingState {
  completed: boolean;
  mascot: string | null;
}

const ONBOARDING_KEY = "pohvala.onboarding.mascot";

export async function loadOnboarding(storage: OnboardingStorage): Promise<OnboardingState> {
  let value: string | null;
  try {
    value = await storage.get();
  } catch {
    // If storage is unavailable we simply show onboarding again rather than crash.
    return { completed: false, mascot: null };
  }
  const completed = value !== null && value !== "";
  return { completed, mascot: completed ? value : null };
}

export async function saveOnboarding(storage: OnboardingStorage, mascot: string): Promise<void> {
  await storage.set(mascot);
}

export async function completeOnboarding(
  storage: OnboardingStorage,
  mascot: string,
  activate: (code: string) => Promise<void>,
): Promise<void> {
  await activate(mascot);
  await saveOnboarding(storage, mascot);
}

export function telegramOnboardingStorage(): OnboardingStorage {
  // telegram-web-app.js always defines CloudStorage, but outside a real Telegram
  // host (browser dev, old clients ≈ v6.0) every call errors with "not supported".
  // Mirror the encryption-key storage in telegram.ts: try CloudStorage, then fall
  // back to device-local storage instead of failing the whole onboarding.
  const cloud = window.Telegram?.WebApp.CloudStorage;

  return {
    get: async () => {
      if (cloud) {
        try {
          return await new Promise<string | null>((resolve, reject) => {
            cloud.getItem("onboarding_mascot", (error, value) => {
              if (error) reject(error);
              else resolve(value || null);
            });
          });
        } catch {
          // Fall back to device-local storage when CloudStorage is unsupported.
        }
      }
      return localStorage.getItem(ONBOARDING_KEY);
    },
    set: async (value) => {
      if (cloud) {
        try {
          await new Promise<void>((resolve, reject) => {
            cloud.setItem("onboarding_mascot", value, (error) => {
              if (error) reject(error);
              else resolve();
            });
          });
          return;
        } catch {
          // Fall back to device-local storage when CloudStorage is unsupported.
        }
      }
      localStorage.setItem(ONBOARDING_KEY, value);
    },
  };
}
