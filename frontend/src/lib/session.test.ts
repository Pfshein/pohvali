import { describe, expect, it, vi } from "vitest";

import type { TelegramClient } from "./telegram";
import { openSession } from "./session";

function fakeTelegramClient(): TelegramClient {
  return {
    mode: "telegram",
    initialize() {},
    getInitData: async () => "query_id=raw%2Bvalue&hash=trusted",
    getFirstName: () => undefined,
    getTimezone: () => "Europe/Moscow",
  };
}

describe("session transport", () => {
  it("sends only raw initData and timezone to the session endpoint", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      id: "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d",
      timezone: "Europe/Moscow",
      telegram_id: 42,
      first_name: "must be ignored",
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    const profile = await openSession(fakeTelegramClient(), fetcher);

    expect(fetcher).toHaveBeenCalledWith("/api/v1/session", {
      method: "POST",
      headers: {
        Authorization: "tma query_id=raw%2Bvalue&hash=trusted",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ timezone: "Europe/Moscow" }),
    });
    expect(profile).toEqual({
      id: "0ecaf26f-ee72-4f06-ae79-41198dd1ac6d",
      timezone: "Europe/Moscow",
    });
  });

  it("returns a generic error without exposing the response body", async () => {
    const fetcher = vi.fn(async () => new Response(
      "sensitive upstream detail",
      { status: 401 },
    ));

    await expect(openSession(fakeTelegramClient(), fetcher)).rejects.toThrow(
      "Could not open Telegram session",
    );
  });
});
