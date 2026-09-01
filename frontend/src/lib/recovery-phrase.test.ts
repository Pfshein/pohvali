import { afterEach, describe, expect, it, vi } from "vitest";

import { decryptPraise, encryptPraise, exportEncryptionKey, generateEncryptionKey } from "./crypto";
import { type KeyStorage } from "./encryption-key";
import {
  createRecoveryPhrase,
  importRecoveryPhrase,
  RecoveryPhraseError,
  restoreEncryptionKey,
} from "./recovery-phrase";

function memoryStorage(): KeyStorage & { value: string | null; writes: number } {
  return {
    value: null,
    writes: 0,
    async getKey() {
      return this.value;
    },
    async setKey(value: string) {
      this.value = value;
      this.writes += 1;
    },
  };
}

describe("recovery phrase v1", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("exports a versioned phrase and imports the same usable key", async () => {
    const original = await generateEncryptionKey();
    const encrypted = await encryptPraise("я сегодня не торопился", original);

    const phrase = await createRecoveryPhrase(original);
    const restored = await importRecoveryPhrase(phrase);

    expect(phrase).toMatch(/^pohvala-v1\.[A-Za-z0-9_-]{43}\.[a-f0-9]{16}$/);
    await expect(decryptPraise(encrypted, restored)).resolves.toBe("я сегодня не торопился");
  });

  it("rejects a phrase whose key payload was changed", async () => {
    const phrase = await createRecoveryPhrase(await generateEncryptionKey());
    const [version, payload, checksum] = phrase.split(".") as [string, string, string];
    const changed = payload.startsWith("A") ? `B${payload.slice(1)}` : `A${payload.slice(1)}`;

    await expect(importRecoveryPhrase(`${version}.${changed}.${checksum}`)).rejects.toMatchObject({
      reason: "checksum",
    });
  });

  it("rejects unknown versions and malformed phrases", async () => {
    const phrase = await createRecoveryPhrase(await generateEncryptionKey());

    await expect(importRecoveryPhrase(phrase.replace("pohvala-v1", "pohvala-v2"))).rejects.toMatchObject({
      reason: "version",
    });
    await expect(importRecoveryPhrase("not a recovery phrase")).rejects.toBeInstanceOf(
      RecoveryPhraseError,
    );
  });

  it("persists an imported key only after the checksum is valid", async () => {
    const key = await generateEncryptionKey();
    const phrase = await createRecoveryPhrase(key);
    const storage = memoryStorage();

    const restored = await restoreEncryptionKey(storage, `  ${phrase}\n`);

    expect(storage.writes).toBe(1);
    expect(storage.value).toBe(await exportEncryptionKey(key));
    expect(await exportEncryptionKey(restored)).toBe(storage.value);

    const invalidStorage = memoryStorage();
    const replacement = phrase.endsWith("0") ? "1" : "0";
    await expect(
      restoreEncryptionKey(invalidStorage, `${phrase.slice(0, -1)}${replacement}`),
    ).rejects.toBeInstanceOf(RecoveryPhraseError);
    expect(invalidStorage.writes).toBe(0);
  });

  it("never sends the key or phrase over the network", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const key = await generateEncryptionKey();

    const phrase = await createRecoveryPhrase(key);
    await restoreEncryptionKey(memoryStorage(), phrase);

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
