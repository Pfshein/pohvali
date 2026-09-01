import { exportEncryptionKey, importEncryptionKey } from "./crypto";
import { KeyStorageError, type KeyStorage } from "./encryption-key";

const RECOVERY_VERSION = "pohvala-v1";
const PAYLOAD_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const CHECKSUM_PATTERN = /^[a-f0-9]{16}$/;

export type RecoveryPhraseErrorReason = "format" | "version" | "checksum" | "key";

export class RecoveryPhraseError extends Error {
  readonly reason: RecoveryPhraseErrorReason;

  constructor(reason: RecoveryPhraseErrorReason, cause?: unknown) {
    super("Recovery phrase is invalid");
    this.name = "RecoveryPhraseError";
    this.reason = reason;
    this.cause = cause;
  }
}

function base64ToBase64Url(value: string): string {
  return value.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function base64UrlToBase64(value: string): string {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  return base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
}

async function checksumFor(payload: string): Promise<string> {
  const input = new TextEncoder().encode(`${RECOVERY_VERSION}:${payload}`);
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", input));
  return Array.from(digest.slice(0, 8), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function equalChecksum(left: string, right: string): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

export async function createRecoveryPhrase(key: CryptoKey): Promise<string> {
  const payload = base64ToBase64Url(await exportEncryptionKey(key));
  if (!PAYLOAD_PATTERN.test(payload)) throw new RecoveryPhraseError("key");
  return `${RECOVERY_VERSION}.${payload}.${await checksumFor(payload)}`;
}

export async function importRecoveryPhrase(phrase: string): Promise<CryptoKey> {
  const parts = phrase.trim().split(".");
  if (parts.length !== 3) throw new RecoveryPhraseError("format");

  const version = parts[0]!;
  const payload = parts[1]!;
  const checksum = parts[2]!;
  if (version !== RECOVERY_VERSION) throw new RecoveryPhraseError("version");
  if (!PAYLOAD_PATTERN.test(payload) || !CHECKSUM_PATTERN.test(checksum)) {
    throw new RecoveryPhraseError("format");
  }

  const expected = await checksumFor(payload);
  if (!equalChecksum(checksum, expected)) throw new RecoveryPhraseError("checksum");

  try {
    return await importEncryptionKey(base64UrlToBase64(payload));
  } catch (error) {
    throw new RecoveryPhraseError("key", error);
  }
}

export async function restoreEncryptionKey(
  storage: KeyStorage,
  phrase: string,
): Promise<CryptoKey> {
  const key = await importRecoveryPhrase(phrase);
  try {
    await storage.setKey(await exportEncryptionKey(key));
  } catch (error) {
    throw new KeyStorageError(error);
  }
  return key;
}
