import { describe, expect, it, vi } from "vitest";

import type { TelegramClient } from "./telegram";
import { loadReminderSettings, setRemindersEnabled } from "./reminders-api";

function fakeTelegramClient(): TelegramClient {
  return {
    mode: "telegram",
    initialize() {},
    getInitData: async () => "query_id=raw%2Bvalue&hash=trusted",
    getFirstName: () => undefined,
    getTimezone: () => "Europe/Moscow",
  };
}

describe("reminder settings transport", () => {
  it("loads settings with the Telegram authorization header", async () => {
    const fetcher = vi.fn(async () => new Response(
      JSON.stringify({ enabled: true, dm_available: false }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    const settings = await loadReminderSettings(fakeTelegramClient(), fetcher);

    expect(fetcher).toHaveBeenCalledWith("/api/v1/reminders", {
      method: "GET",
      headers: {
        Authorization: "tma query_id=raw%2Bvalue&hash=trusted",
      },
    });
    expect(settings).toEqual({ enabled: true, dmAvailable: false });
  });

  it("rejects a malformed settings payload with a generic error", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ enabled: "yes" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));

    await expect(loadReminderSettings(fakeTelegramClient(), fetcher)).rejects.toThrow(
      "Could not load reminder settings",
    );
  });

  it("sends an explicit enable choice and returns the stored settings", async () => {
    const fetcher = vi.fn(async () => new Response(
      JSON.stringify({ enabled: false, dm_available: true }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    const settings = await setRemindersEnabled(fakeTelegramClient(), false, fetcher);

    expect(fetcher).toHaveBeenCalledWith("/api/v1/reminders", {
      method: "PUT",
      headers: {
        Authorization: "tma query_id=raw%2Bvalue&hash=trusted",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled: false }),
    });
    expect(settings).toEqual({ enabled: false, dmAvailable: true });
  });

  it("returns a generic error without exposing the response body", async () => {
    const fetcher = vi.fn(async () => new Response("sensitive upstream detail", { status: 401 }));

    await expect(setRemindersEnabled(fakeTelegramClient(), true, fetcher)).rejects.toThrow(
      "Could not change reminder settings",
    );
  });
});
