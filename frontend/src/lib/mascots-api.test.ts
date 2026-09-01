import { describe, expect, it, vi } from "vitest";

import { activateMascot, loadCollection, purchaseMascot } from "./mascots-api";
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

const COLLECTION = {
  balance: 12,
  active_mascot: "ava",
  mascots: [
    {
      code: "ava",
      name: "Авокадо Ава",
      blurb: "Спокойная и тёплая",
      asset_path: "/assets/mascots/ava.png",
      starter: true,
      price: null,
      state: "owned",
      unlocked: true,
      active: true,
    },
    {
      code: "tisha",
      name: "Капибара Тиша",
      blurb: "Добрая и невозмутимая",
      asset_path: "/assets/mascots/tisha.png",
      starter: false,
      price: 10,
      state: "affordable",
      unlocked: true,
      active: false,
    },
  ],
};

describe("loading the collection", () => {
  it("sends one authorized GET and maps to camelCase", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(COLLECTION), { status: 200 }));

    const collection = await loadCollection(fakeClient(), fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/mascots");
    expect(init.method).toBe("GET");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");

    expect(collection.balance).toBe(12);
    expect(collection.activeMascot).toBe("ava");
    expect(collection.mascots[1]).toEqual({
      code: "tisha",
      name: "Капибара Тиша",
      blurb: "Добрая и невозмутимая",
      assetPath: "/assets/mascots/tisha.png",
      starter: false,
      price: 10,
      state: "affordable",
      unlocked: true,
      active: false,
    });
  });

  it("throws when the payload shape is wrong", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ balance: 1 }), { status: 200 }));

    await expect(loadCollection(fakeClient(), fetcher)).rejects.toThrow("Could not load the collection");
  });

  it("throws a generic error on a failed request", async () => {
    const fetcher = vi.fn(async () => new Response("nope", { status: 401 }));

    await expect(loadCollection(fakeClient(), fetcher)).rejects.toThrow("Could not load the collection");
  });
});

describe("purchasing a mascot", () => {
  it("POSTs to the purchase endpoint and returns the outcome", async () => {
    const body = { code: "tisha", state: "owned", balance: 2, newly_purchased: true };
    const fetcher = vi.fn(async () => new Response(JSON.stringify(body), { status: 200 }));

    const outcome = await purchaseMascot(fakeClient(), "tisha", fetcher);

    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/mascots/tisha/purchase");
    expect(init.method).toBe("POST");
    expect(outcome).toEqual({ code: "tisha", balance: 2, newlyPurchased: true });
  });

  it("throws a calm error when the purchase is rejected", async () => {
    const fetcher = vi.fn(async () => new Response("locked", { status: 409 }));

    await expect(purchaseMascot(fakeClient(), "bim", fetcher)).rejects.toThrow(
      "Could not open this companion",
    );
  });
});

describe("activating a mascot", () => {
  it("sends one authorized PUT", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ active_mascot: "tisha" }), { status: 200 }));

    await activateMascot(fakeClient(), "tisha", fetcher);

    const [url, init] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/mascots/tisha/active");
    expect(init.method).toBe("PUT");
    expect((init.headers as Record<string, string>).Authorization).toBe("tma init-raw");
  });

  it("throws when activation is refused", async () => {
    const fetcher = vi.fn(async () => new Response("not owned", { status: 409 }));

    await expect(activateMascot(fakeClient(), "bim", fetcher)).rejects.toThrow(
      "Could not choose this companion",
    );
  });
});
