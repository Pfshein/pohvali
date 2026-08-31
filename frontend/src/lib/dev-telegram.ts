const DEV_BOT_TOKEN = "dev-token";
const DEV_USER = { id: 900000001, first_name: "Друг" } as const;

async function hmacSha256(key: BufferSource, value: string): Promise<ArrayBuffer> {
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    key,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return crypto.subtle.sign("HMAC", cryptoKey, new TextEncoder().encode(value));
}

function toHex(value: ArrayBuffer): string {
  return Array.from(new Uint8Array(value), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function createDevInitData(now: Date): Promise<string> {
  const values = {
    auth_date: String(Math.floor(now.getTime() / 1000)),
    query_id: "pohvala-browser-dev",
    user: JSON.stringify(DEV_USER),
  };
  const dataCheckString = Object.entries(values)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}=${value}`)
    .join("\n");
  const secretKey = await hmacSha256(
    new TextEncoder().encode("WebAppData"),
    DEV_BOT_TOKEN,
  );
  const hash = toHex(await hmacSha256(secretKey, dataCheckString));

  return new URLSearchParams({ ...values, hash }).toString();
}

export function getDevFirstName(): string {
  return DEV_USER.first_name;
}
