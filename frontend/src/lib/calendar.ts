import type { TelegramClient } from "./telegram";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface CalendarDay {
  localDate: string;
  count: number;
}

export interface MonthRef {
  year: number;
  month: number;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function currentMonth(now: Date = new Date()): MonthRef {
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

export function monthRange({ year, month }: MonthRef): { from: string; to: string } {
  const lastDay = new Date(year, month, 0).getDate();
  const prefix = `${year}-${pad(month)}`;
  return { from: `${prefix}-01`, to: `${prefix}-${pad(lastDay)}` };
}

export function dateInMonth({ year, month }: MonthRef, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`;
}

/** The client's own calendar date as ``YYYY-MM-DD`` (local time, not UTC). */
export function todayIsoDate(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/**
 * Whether an ``YYYY-MM-DD`` date is still ahead of the client's today. You can
 * only praise yourself for today or a day that has already happened, so a
 * future day is never a valid save target. ISO dates sort lexicographically,
 * so a plain string comparison is a correct date comparison here.
 */
export function isFutureIsoDate(isoDate: string, now: Date = new Date()): boolean {
  return isoDate > todayIsoDate(now);
}

export function markedDaysForMonth(
  days: readonly CalendarDay[],
  month: MonthRef,
): ReadonlySet<number> {
  const prefix = `${month.year}-${pad(month.month)}-`;
  return new Set(
    days
      .filter((day) => day.count > 0 && day.localDate.startsWith(prefix))
      .map((day) => Number(day.localDate.slice(prefix.length)))
      .filter((day) => Number.isInteger(day) && day >= 1 && day <= 31),
  );
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
