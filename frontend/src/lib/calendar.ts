import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface CalendarDay {
  localDate: string;
  count: number;
}

export async function loadCalendar(
  client: TelegramClient,
  from: string,
  to: string,
  fetcher: Fetcher = fetch,
): Promise<CalendarDay[]> {
  const initData = await client.getInitData();
  const query = `?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;

  const response = await fetcher(`/api/v1/calendar${query}`, {
    method: "GET",
    headers: { Authorization: `tma ${initData}` },
  });

  if (!response.ok) throw new Error("Could not load calendar");

  const payload: unknown = await response.json();
  if (!Array.isArray(payload)) throw new Error("Could not load calendar");

  const days: CalendarDay[] = [];
  for (const item of payload) {
    if (
      typeof item === "object"
      && item !== null
      && "local_date" in item
      && typeof item.local_date === "string"
      && "count" in item
      && typeof item.count === "number"
    ) {
      days.push({ localDate: item.local_date, count: item.count });
    }
  }
  return days;
}
