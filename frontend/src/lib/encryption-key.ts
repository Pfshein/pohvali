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
