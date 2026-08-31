const KEY_ALGORITHM = "AES-GCM";
const KEY_LENGTH = 256;
const IV_BYTES = 12;

export interface EncryptedPraise {
  ciphertext: string;
  iv: string;
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export async function generateEncryptionKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: KEY_ALGORITHM, length: KEY_LENGTH },
    true,
    ["encrypt", "decrypt"],
  );
}

export async function exportEncryptionKey(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey("raw", key);
  return bytesToBase64(new Uint8Array(raw));
}

export async function importEncryptionKey(encoded: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    base64ToBytes(encoded),
    { name: KEY_ALGORITHM },
    true,
    ["encrypt", "decrypt"],
  );
}

export async function encryptPraise(text: string, key: CryptoKey): Promise<EncryptedPraise> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const plaintext = new TextEncoder().encode(text);
  const ciphertext = await crypto.subtle.encrypt({ name: KEY_ALGORITHM, iv }, key, plaintext);
  return {
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
    iv: bytesToBase64(iv),
  };
}

export async function decryptPraise(
  encrypted: EncryptedPraise,
  key: CryptoKey,
): Promise<string> {
  const plaintext = await crypto.subtle.decrypt(
    { name: KEY_ALGORITHM, iv: base64ToBytes(encrypted.iv) },
    key,
    base64ToBytes(encrypted.ciphertext),
  );
  return new TextDecoder().decode(plaintext);
}

