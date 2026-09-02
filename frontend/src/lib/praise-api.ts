import type { PraiseCreated } from "./api";
import { decryptPraise, encryptPraise } from "./crypto";
import { normalizePraise } from "./praise";
import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface DayEntry {
  id: string;
  local_date: string;
  created_at: string;
  text: string | null;
  unreadable: boolean;
}

/**
 * Day entries after a praise was saved. The composer already holds the
 * plaintext, so a freshly saved praise is folded into the open day straight
 * away instead of waiting for a reload to fetch and decrypt it again.
 * Entries stay ordered oldest first, the same order the server returns.
 */
export function dayEntriesAfterSave(
  entries: DayEntry[] | null,
  selectedDate: string | null,
  created: PraiseCreated,
  text: string,
  createdAt: string = new Date().toISOString(),
): DayEntry[] | null {
  if (entries === null) return null;
  if (selectedDate !== created.local_date) return entries;
  if (entries.some((entry) => entry.id === created.id)) return entries;
  return [
    ...entries,
    {
      id: created.id,
      local_date: created.local_date,
      created_at: createdAt,
      text,
      unreadable: false,
    },
  ];
}

export async function savePraise(
  client: TelegramClient,
  key: CryptoKey,
  text: string,
  fetcher: Fetcher = fetch,
): Promise<PraiseCreated> {
  const { ciphertext, iv } = await encryptPraise(normalizePraise(text), key);
  const initData = await client.getInitData();

  const response = await fetcher("/api/v1/praises", {
    method: "POST",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ body_ciphertext: ciphertext, iv }),
  });

  if (!response.ok) throw new Error("Could not save praise");

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object"
    || payload === null
    || !("id" in payload)
    || typeof payload.id !== "string"
    || !("local_date" in payload)
    || typeof payload.local_date !== "string"
    || !("star_awarded" in payload)
    || typeof payload.star_awarded !== "boolean"
    || !("balance" in payload)
    || typeof payload.balance !== "number"
    || !("newly_unlocked" in payload)
    || !Array.isArray(payload.newly_unlocked)
    || !payload.newly_unlocked.every((code) => typeof code === "string")
  ) {
    throw new Error("Could not save praise");
  }

  return {
    id: payload.id,
    local_date: payload.local_date,
    star_awarded: payload.star_awarded,
    balance: payload.balance,
    newly_unlocked: payload.newly_unlocked,
  };
}

export async function editPraise(
  client: TelegramClient,
  key: CryptoKey,
  id: string,
  text: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  const { ciphertext, iv } = await encryptPraise(normalizePraise(text), key);
  const initData = await client.getInitData();

  const response = await fetcher(`/api/v1/praises/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ body_ciphertext: ciphertext, iv }),
  });

  if (!response.ok) throw new Error("Could not edit praise");
}

export async function deletePraise(
  client: TelegramClient,
  id: string,
  fetcher: Fetcher = fetch,
): Promise<void> {
  const initData = await client.getInitData();

  const response = await fetcher(`/api/v1/praises/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not delete praise");
}

function isEntryShape(
  value: unknown,
): value is { id: string; local_date: string; created_at: string; iv: string; body_ciphertext: string } {
  return (
    typeof value === "object"
    && value !== null
    && "id" in value && typeof value.id === "string"
    && "local_date" in value && typeof value.local_date === "string"
    && "created_at" in value && typeof value.created_at === "string"
    && "iv" in value && typeof value.iv === "string"
    && "body_ciphertext" in value && typeof value.body_ciphertext === "string"
  );
}

export async function loadDay(
  client: TelegramClient,
  key: CryptoKey,
  date?: string,
  fetcher: Fetcher = fetch,
): Promise<DayEntry[]> {
  const initData = await client.getInitData();
  const query = date ? `?date=${encodeURIComponent(date)}` : "";

  const response = await fetcher(`/api/v1/praises${query}`, {
    method: "GET",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not load praises");

  const payload: unknown = await response.json();
  if (!Array.isArray(payload)) throw new Error("Could not load praises");

  const entries: DayEntry[] = [];
  for (const item of payload) {
    if (!isEntryShape(item)) continue;
    const base = { id: item.id, local_date: item.local_date, created_at: item.created_at };
    try {
      const text = await decryptPraise(
        { ciphertext: item.body_ciphertext, iv: item.iv },
        key,
      );
      entries.push({ ...base, text, unreadable: false });
    } catch {
      entries.push({ ...base, text: null, unreadable: true });
    }
  }
  return entries;
}
