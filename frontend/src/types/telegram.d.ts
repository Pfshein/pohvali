interface TelegramCloudStorage {
  getItem(key: string, callback: (error: Error | null, value?: string) => void): void;
  setItem(key: string, value: string, callback?: (error: Error | null, stored?: boolean) => void): void;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: {
    user?: { first_name?: string };
  };
  CloudStorage?: TelegramCloudStorage;
  ready(): void;
  expand(): void;
}

interface Window {
  Telegram?: { WebApp: TelegramWebApp };
}

