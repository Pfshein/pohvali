import { describe, expect, it, vi } from "vitest";

import { generateEncryptionKey } from "./crypto";
import { deletePraise, editPraise } from "./praise-api";
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

describe("editing a praise", () => {
  it("re-encrypts and PATCHes the entry once", async () => {
    const key = await generateEncryptionKey();
    const fetcher = vi.fn(async () => new Response(null, { status: 204 }));

    await editPraise(fakeClient(), key, "abc-123", "Новая версия", "ava-happy", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/praises/abc-123");
    expect(init.method).toBe("PATCH");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");
    const body = JSON.parse(init.body as string);
    expect(Object.keys(body).sort()).toEqual(["body_ciphertext", "iv", "sticker"]);
    expect(body.sticker).toBe("ava-happy");
    expect(body.body_ciphertext).not.toContain("версия");
  });

  it("throws a generic error when the request fails", async () => {
    const key = await generateEncryptionKey();
    const fetcher = vi.fn(async () => new Response("nope", { status: 404 }));

    await expect(
      editPraise(fakeClient(), key, "abc-123", "текст", null, fetcher),
    ).rejects.toThrow("Could not edit praise");
  });
});

describe("deleting a praise", () => {
  it("sends one authorized DELETE", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 204 }));

    await deletePraise(fakeClient(), "abc-123", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/praises/abc-123");
    expect(init.method).toBe("DELETE");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");
  });

  it("throws a generic error when the request fails", async () => {
    const fetcher = vi.fn(async () => new Response("nope", { status: 404 }));

    await expect(deletePraise(fakeClient(), "abc-123", fetcher)).rejects.toThrow(
      "Could not delete praise",
    );
  });
});
