import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface ReminderSettings {
  enabled: boolean;
  dmAvailable: boolean;
}

export interface ReminderControls {
  load: () => Promise<ReminderSettings>;
  setEnabled: (enabled: boolean) => Promise<ReminderSettings>;
}

function parseSettings(payload: unknown): ReminderSettings {
  if (
    typeof payload !== "object"
    || payload === null
    || !("enabled" in payload) || typeof (payload as { enabled: unknown }).enabled !== "boolean"
    || !("dm_available" in payload)
    || typeof (payload as { dm_available: unknown }).dm_available !== "boolean"
  ) {
    throw new Error("Malformed reminder settings");
  }
  const { enabled, dm_available } = payload as { enabled: boolean; dm_available: boolean };
  return { enabled, dmAvailable: dm_available };
}

export async function loadReminderSettings(
  client: TelegramClient,
  fetcher: Fetcher = fetch,
): Promise<ReminderSettings> {
  const initData = await client.getInitData();
  const response = await fetcher("/api/v1/reminders", {
    method: "GET",
    headers: {
      Authorization: `tma ${initData}`,
    },
  });

  if (!response.ok) throw new Error("Could not load reminder settings");
  try {
    return parseSettings(await response.json());
  } catch {
    throw new Error("Could not load reminder settings");
  }
}

export async function setRemindersEnabled(
  client: TelegramClient,
  enabled: boolean,
  fetcher: Fetcher = fetch,
): Promise<ReminderSettings> {
  const initData = await client.getInitData();
  const response = await fetcher("/api/v1/reminders", {
    method: "PUT",
    headers: {
      Authorization: `tma ${initData}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ enabled }),
  });

  if (!response.ok) throw new Error("Could not change reminder settings");
  try {
    return parseSettings(await response.json());
  } catch {
    throw new Error("Could not change reminder settings");
  }
}
