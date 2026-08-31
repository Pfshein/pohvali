import type { SessionProfile } from "./api";
import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export async function openSession(
  client: TelegramClient,
  fetcher: Fetcher = fetch,
): Promise<SessionProfile> {
  const initData = await client.getInitData();
  const response = await fetcher("/api/v1/session", {
    method: "POST",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ timezone: client.getTimezone() }),
  });

  if (!response.ok) throw new Error("Could not open Telegram session");

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object"
    || payload === null
    || !("id" in payload)
    || typeof payload.id !== "string"
    || !("timezone" in payload)
    || typeof payload.timezone !== "string"
  ) {
    throw new Error("Could not open Telegram session");
  }

  return { id: payload.id, timezone: payload.timezone };
}
