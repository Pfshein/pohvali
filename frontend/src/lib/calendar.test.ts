import { describe, expect, it, vi } from "vitest";

import {
  dateInMonth,
  isFutureIsoDate,
  loadCalendar,
  markedDaysForMonth,
  monthRange,
  todayIsoDate,
} from "./calendar";
import type { TelegramClient } from "./telegram";

function fakeClient(): TelegramClient {
  return {
    mode: "telegram",
    initialize() {},
    getInitData: async () => "init-raw",
    getFirstName: () => undefined,
    getTimezone: () => "UTC",
  };
}

describe("calendar loading", () => {
  it("builds real month boundaries, including leap years", () => {
    expect(monthRange({ year: 2028, month: 2 })).toEqual({
      from: "2028-02-01",
      to: "2028-02-29",
    });
    expect(dateInMonth({ year: 2026, month: 9 }, 3)).toBe("2026-09-03");
  });

  it("reads today from the client clock in local time, not UTC", () => {
    // 2026-09-02 23:30 in a UTC+3 zone is still 2026-09-02 for the client,
    // even though UTC has already rolled over to the 3rd.
    const lateEvening = new Date(2026, 8, 2, 23, 30);

    expect(todayIsoDate(lateEvening)).toBe("2026-09-02");
  });

  it("treats only days after the client's today as future", () => {
    const now = new Date(2026, 8, 2, 12, 0);

    expect(isFutureIsoDate("2026-09-03", now)).toBe(true);
    expect(isFutureIsoDate("2026-10-01", now)).toBe(true);
    expect(isFutureIsoDate("2027-01-01", now)).toBe(true);
    expect(isFutureIsoDate("2026-09-02", now)).toBe(false);
    expect(isFutureIsoDate("2026-09-01", now)).toBe(false);
    expect(isFutureIsoDate("2026-08-31", now)).toBe(false);
    expect(isFutureIsoDate("2025-12-31", now)).toBe(false);
  });

  it("maps only marked dates from the requested month", () => {
    const marked = markedDaysForMonth([
      { localDate: "2026-08-31", count: 1 },
      { localDate: "2026-09-01", count: 2 },
      { localDate: "2026-09-03", count: 0 },
    ], { year: 2026, month: 9 });

    expect([...marked]).toEqual([1]);
  });

  it("fetches a bounded range once and maps marked days", async () => {
    const fetcher = vi.fn(async () => new Response(
      JSON.stringify([
        { local_date: "2026-09-01", count: 3 },
        { local_date: "2026-09-03", count: 1 },
      ]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    const days = await loadCalendar(fakeClient(), "2026-09-01", "2026-09-30", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/calendar?from=2026-09-01&to=2026-09-30");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");
    expect(days).toEqual([
      { localDate: "2026-09-01", count: 3 },
      { localDate: "2026-09-03", count: 1 },
    ]);
  });

  it("throws a generic error when the request fails", async () => {
    const fetcher = vi.fn(async () => new Response("sensitive", { status: 422 }));

    await expect(
      loadCalendar(fakeClient(), "2026-09-01", "2026-09-30", fetcher),
    ).rejects.toThrow("Could not load calendar");
  });
});
