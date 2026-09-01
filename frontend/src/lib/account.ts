import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export type DeletionStep = "idle" | "confirm" | "working" | "done" | "error";
export type DeletionEvent = "request" | "cancel" | "confirm" | "succeeded" | "failed";

const ALLOWED_EVENTS: Record<DeletionStep, DeletionEvent[]> = {
  idle: ["request"],
  confirm: ["cancel", "confirm"],
  working: ["succeeded", "failed"],
  done: [],
  error: ["request", "cancel"],
};

export function nextDeletionStep(current: DeletionStep, event: DeletionEvent): DeletionStep {
  if (!ALLOWED_EVENTS[current].includes(event)) return current;
  switch (event) {
    case "request":
      return "confirm";
    case "confirm":
      return "working";
    case "cancel":
      return "idle";
    case "succeeded":
      return "done";
    case "failed":
      return "error";
  }
}

export async function deleteAccountData(
  client: TelegramClient,
  fetcher: Fetcher = fetch,
): Promise<void> {
  const initData = await client.getInitData();
  const response = await fetcher("/api/v1/session", {
    method: "DELETE",
    headers: {
      Authorization: `tma ${initData}`,
    },
  });

  if (!response.ok) throw new Error("Could not delete account data");
}
