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
  const cloud = window.Telegram?.WebApp.CloudStorage;

  if (!cloud) {
    return {
      get: async () => localStorage.getItem(ONBOARDING_KEY),
      set: async (value) => localStorage.setItem(ONBOARDING_KEY, value),
    };
  }

  return {
    get: () =>
      new Promise((resolve, reject) => {
        cloud.getItem("onboarding_mascot", (error, value) => {
          if (error) reject(error);
          else resolve(value || null);
        });
      }),
    set: (value) =>
      new Promise((resolve, reject) => {
        cloud.setItem("onboarding_mascot", value, (error) => {
          if (error) reject(error);
          else resolve();
        });
      }),
  };
}
