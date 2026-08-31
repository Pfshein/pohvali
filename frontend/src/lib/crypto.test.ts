import { describe, expect, it } from "vitest";

import {
  decryptPraise,
  encryptPraise,
  exportEncryptionKey,
  generateEncryptionKey,
  importEncryptionKey,
} from "./crypto";

describe("praise encryption", () => {
  it("round-trips Cyrillic text through an exported key", async () => {
    const key = await generateEncryptionKey();
    const restoredKey = await importEncryptionKey(await exportEncryptionKey(key));
    const encrypted = await encryptPraise("Я попросил о помощи", restoredKey);

    expect(encrypted.ciphertext).not.toContain("помощи");
    await expect(decryptPraise(encrypted, restoredKey)).resolves.toBe("Я попросил о помощи");
  });

  it("uses a fresh IV for every encryption", async () => {
    const key = await generateEncryptionKey();

    const first = await encryptPraise("одинаковый текст", key);
    const second = await encryptPraise("одинаковый текст", key);

    expect(first.iv).not.toBe(second.iv);
    expect(first.ciphertext).not.toBe(second.ciphertext);
  });
});

