import { afterEach, describe, expect, it, vi } from "vitest";

import { decryptPraise, encryptPraise } from "./crypto";
import { KeyStorageError, loadOrCreateEncryptionKey, type KeyStorage } from "./encryption-key";

function memoryStorage(
  initial: string | null = null,
): KeyStorage & { value: string | null; writes: number } {
  return {
    value: initial,
    writes: 0,
    async getKey() {
      return this.value;
    },
    async setKey(value: string) {
      this.writes += 1;
      this.value = value;
    },
  };
}

describe("encryption key lifecycle", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("generates and persists a usable key on first run", async () => {
    const storage = memoryStorage();

    const key = await loadOrCreateEncryptionKey(storage);
    const encrypted = await encryptPraise("привет", key);

    expect(storage.value).not.toBeNull();
    expect(storage.writes).toBe(1);
    await expect(decryptPraise(encrypted, key)).resolves.toBe("привет");
  });

  it("reuses the stored key without writing again", async () => {
    const first = memoryStorage();
    const key = await loadOrCreateEncryptionKey(first);
    const encrypted = await encryptPraise("одно и то же", key);

    const second = memoryStorage(first.value);
    const reused = await loadOrCreateEncryptionKey(second);

    expect(second.writes).toBe(0);
    await expect(decryptPraise(encrypted, reused)).resolves.toBe("одно и то же");
  });

  it("never touches the network", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    await loadOrCreateEncryptionKey(memoryStorage());

    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("wraps a read failure in KeyStorageError", async () => {
    const storage: KeyStorage = {
      getKey: async () => {
        throw new Error("cloud storage offline");
      },
      setKey: async () => {},
    };

    await expect(loadOrCreateEncryptionKey(storage)).rejects.toBeInstanceOf(KeyStorageError);
  });

  it("wraps a write failure in KeyStorageError", async () => {
    const storage: KeyStorage = {
      getKey: async () => null,
      setKey: async () => {
        throw new Error("quota exceeded");
      },
    };

    await expect(loadOrCreateEncryptionKey(storage)).rejects.toBeInstanceOf(KeyStorageError);
  });

  it("wraps a corrupt stored value in KeyStorageError", async () => {
    await expect(
      loadOrCreateEncryptionKey(memoryStorage("not-a-real-key")),
    ).rejects.toBeInstanceOf(KeyStorageError);
  });
});
