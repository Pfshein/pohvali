const DEV_KEY_STORAGE = "pohvala.dev.enc_key";

export type TelegramMode = "telegram" | "mock";

export interface TelegramClient {
  readonly mode: TelegramMode;
  initialize(): void;
  getInitData(): Promise<string>;
  getFirstName(): string | undefined;
  getTimezone(): string;
}

interface TelegramClientOptions {
  mode?: TelegramMode;
  webApp?: TelegramWebApp;
  mock?: {
    createInitData: (now: Date) => Promise<string>;
    firstName: string;
  };
  now?: () => Date;
  resolveTimezone?: () => string;
}

export function createTelegramClient({
  mode = "telegram",
  webApp,
  mock,
  now = () => new Date(),
  resolveTimezone = () => Intl.DateTimeFormat().resolvedOptions().timeZone,
}: TelegramClientOptions = {}): TelegramClient {
  return {
    mode,
    initialize() {
      if (mode === "telegram") {
        webApp?.ready();
        webApp?.expand();
      }
    },
    async getInitData() {
      if (mode === "mock" && mock) return mock.createInitData(now());
      if (mode === "telegram" && webApp?.initData) return webApp.initData;
      throw new Error("Telegram Mini App is unavailable");
    },
    getFirstName() {
      return mode === "mock"
        ? mock?.firstName
        : webApp?.initDataUnsafe?.user?.first_name;
    },
    getTimezone() {
      try {
        return resolveTimezone() || "UTC";
      } catch {
        return "UTC";
      }
    },
  };
}

function defaultClient(): TelegramClient {
  return createTelegramClient({ webApp: window.Telegram?.WebApp });
}

function cloudStorage(): TelegramCloudStorage | undefined {
  return window.Telegram?.WebApp.CloudStorage;
}

export function initializeTelegram(): void {
  defaultClient().initialize();
}

export function getTelegramInitData(): Promise<string> {
  return defaultClient().getInitData();
}

export function getFirstName(): string | undefined {
  return defaultClient().getFirstName();
}

export function getTimezone(): string {
  return defaultClient().getTimezone();
}

export async function getStoredEncryptionKey(): Promise<string | null> {
  const storage = cloudStorage();
  if (storage) {
    try {
      return await new Promise<string | null>((resolve, reject) => {
        storage.getItem("enc_key", (error, value) => {
          if (error) reject(error);
          else resolve(value || null);
        });
      });
    } catch {
      // Old Telegram clients (≈ v6.0) expose CloudStorage but reject with
      // "not supported"; fall back to device-local storage instead of failing.
    }
  }
  return localStorage.getItem(DEV_KEY_STORAGE);
}

export async function storeEncryptionKey(value: string): Promise<void> {
  const storage = cloudStorage();
  if (storage) {
    try {
      await new Promise<void>((resolve, reject) => {
        storage.setItem("enc_key", value, (error) => {
          if (error) reject(error);
          else resolve();
        });
      });
      return;
    } catch {
      // Fall back to device-local storage when CloudStorage is unsupported.
    }
  }
  localStorage.setItem(DEV_KEY_STORAGE, value);
}
