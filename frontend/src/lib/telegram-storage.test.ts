import { afterEach, describe, expect, it, vi } from "vitest";

import { getStoredEncryptionKey, storeEncryptionKey } from "./telegram";

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

afterEach(() => vi.unstubAllGlobals());

describe("encryption key storage", () => {
  it("uses localStorage when no Telegram CloudStorage is present", async () => {
    const local = fakeLocalStorage();
    vi.stubGlobal("localStorage", local);
    vi.stubGlobal("window", {});

    await storeEncryptionKey("key-abc");
    expect(await getStoredEncryptionKey()).toBe("key-abc");
    expect(local.store.get("pohvala.dev.enc_key")).toBe("key-abc");
  });

  it("falls back to localStorage when CloudStorage errors (old Telegram client)", async () => {
    const local = fakeLocalStorage();
    const cloud = {
      getItem: (_key: string, cb: (e: Error | null, v?: string) => void) =>
        cb(new Error("CloudStorage is not supported in version 6.0")),
      setItem: (_key: string, _value: string, cb?: (e: Error | null) => void) =>
        cb?.(new Error("CloudStorage is not supported in version 6.0")),
    };
    vi.stubGlobal("localStorage", local);
    vi.stubGlobal("window", { Telegram: { WebApp: { CloudStorage: cloud } } });

    await storeEncryptionKey("key-xyz");
    expect(await getStoredEncryptionKey()).toBe("key-xyz");
    expect(local.store.get("pohvala.dev.enc_key")).toBe("key-xyz");
  });

  it("uses CloudStorage when it works", async () => {
    const backing = new Map<string, string>();
    const cloud = {
      getItem: (key: string, cb: (e: Error | null, v?: string) => void) =>
        cb(null, backing.get(key)),
      setItem: (key: string, value: string, cb?: (e: Error | null) => void) => {
        backing.set(key, value);
        cb?.(null);
      },
    };
    vi.stubGlobal("localStorage", fakeLocalStorage());
    vi.stubGlobal("window", { Telegram: { WebApp: { CloudStorage: cloud } } });

    await storeEncryptionKey("cloud-key");
    expect(await getStoredEncryptionKey()).toBe("cloud-key");
    expect(backing.get("enc_key")).toBe("cloud-key");
  });
});
