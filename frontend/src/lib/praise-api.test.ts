import { describe, expect, it, vi } from "vitest";

import { generateEncryptionKey } from "./crypto";
import { savePraise } from "./praise-api";
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

describe("praise submission", () => {
  it("encrypts locally and saves with a single authorized round-trip", async () => {
    const key = await generateEncryptionKey();
    const fetcher = vi.fn(async () => new Response(
      JSON.stringify({
        id: "p1",
        local_date: "2026-09-01",
        star_awarded: true,
        balance: 10,
        newly_unlocked: ["tisha"],
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    ));

    const result = await savePraise(fakeClient(), key, "  Я хорошо поработал  ", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/praises");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");

    const body = JSON.parse(init.body as string);
    expect(Object.keys(body).sort()).toEqual(["body_ciphertext", "iv"]);
    expect(body.body_ciphertext).not.toContain("поработал");
    expect(result).toEqual({
      id: "p1",
      local_date: "2026-09-01",
      star_awarded: true,
      balance: 10,
      newly_unlocked: ["tisha"],
    });
  });

  it("throws a generic error without leaking the response body", async () => {
    const key = await generateEncryptionKey();
    const fetcher = vi.fn(async () => new Response("sensitive upstream detail", { status: 413 }));

    await expect(savePraise(fakeClient(), key, "Я молодец", fetcher)).rejects.toThrow(
      "Could not save praise",
    );
  });
});
