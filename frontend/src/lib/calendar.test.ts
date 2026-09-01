import { describe, expect, it, vi } from "vitest";

import { dateInMonth, loadCalendar, markedDaysForMonth, monthRange } from "./calendar";
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
