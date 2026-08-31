import { describe, expect, it, vi } from "vitest";

import { encryptPraise, generateEncryptionKey } from "./crypto";
import { loadDay } from "./praise-api";
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

describe("reading a day of praise", () => {
  it("decrypts locally and isolates a corrupt entry", async () => {
    const key = await generateEncryptionKey();
    const good = await encryptPraise("Я отдохнул", key);
    const entries = [
      { id: "1", local_date: "2026-09-01", created_at: "2026-09-01T10:00:00Z", ...good },
      {
        id: "2",
        local_date: "2026-09-01",
        created_at: "2026-09-01T11:00:00Z",
        iv: good.iv,
        body_ciphertext: btoa("garbage-that-will-not-decrypt"),
      },
    ].map((entry) => ({
      id: entry.id,
      local_date: entry.local_date,
      created_at: entry.created_at,
      iv: entry.iv,
      body_ciphertext: entry.body_ciphertext ?? entry.ciphertext,
    }));

    const fetcher = vi.fn(async () => new Response(JSON.stringify(entries), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));

    const day = await loadDay(fakeClient(), key, "2026-09-01", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/praises?date=2026-09-01");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");

    expect(day).toHaveLength(2);
    expect(day[0]).toMatchObject({ id: "1", text: "Я отдохнул", unreadable: false });
    expect(day[1]).toMatchObject({ id: "2", text: null, unreadable: true });
  });

  it("throws a generic error when the request fails", async () => {
    const key = await generateEncryptionKey();
    const fetcher = vi.fn(async () => new Response("sensitive", { status: 500 }));

    await expect(loadDay(fakeClient(), key, undefined, fetcher)).rejects.toThrow(
      "Could not load praises",
    );
  });
});
