import { describe, expect, it, vi } from "vitest";

import { loadCalendar } from "./calendar";
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
