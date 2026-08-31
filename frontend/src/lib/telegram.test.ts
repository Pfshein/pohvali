import { describe, expect, it, vi } from "vitest";

import { createDevInitData, getDevFirstName } from "./dev-telegram";
import { createTelegramClient } from "./telegram";

function fakeWebApp(initData = "query_id=raw%2Bvalue&hash=trusted") {
  return {
    initData,
    initDataUnsafe: { user: { first_name: "Аня" } },
    ready: vi.fn(),
    expand: vi.fn(),
  } satisfies TelegramWebApp;
}

describe("Telegram client", () => {
  it("keeps production initData untouched and initializes the WebApp", async () => {
    const webApp = fakeWebApp();
    const client = createTelegramClient({ mode: "telegram", webApp });

    client.initialize();

    expect(webApp.ready).toHaveBeenCalledOnce();
    expect(webApp.expand).toHaveBeenCalledOnce();
    await expect(client.getInitData()).resolves.toBe(
      "query_id=raw%2Bvalue&hash=trusted",
    );
    expect(client.getFirstName()).toBe("Аня");
  });

  it("uses a fresh signed fake identity only in explicit mock mode", async () => {
    const client = createTelegramClient({
      mode: "mock",
      mock: {
        createInitData: createDevInitData,
        firstName: getDevFirstName(),
      },
      now: () => new Date("2026-08-31T12:00:00Z"),
    });

    const initData = await client.getInitData();
    const fields = new URLSearchParams(initData);

    expect(client.mode).toBe("mock");
    expect(fields.get("auth_date")).toBe("1788177600");
    expect(JSON.parse(fields.get("user") ?? "null")).toEqual({
      id: 900000001,
      first_name: "Друг",
    });
    expect(fields.get("hash")).toMatch(/^[a-f0-9]{64}$/);
    expect(client.getFirstName()).toBe("Друг");
  });

  it("keeps mock mode isolated even when a WebApp object is present", async () => {
    const webApp = fakeWebApp("real-user-data");
    const client = createTelegramClient({
      mode: "mock",
      webApp,
      mock: {
        createInitData: createDevInitData,
        firstName: getDevFirstName(),
      },
      now: () => new Date("2026-08-31T12:00:00Z"),
    });

    client.initialize();
    const fields = new URLSearchParams(await client.getInitData());

    expect(JSON.parse(fields.get("user") ?? "null").id).toBe(900000001);
    expect(client.getFirstName()).toBe("Друг");
    expect(webApp.ready).not.toHaveBeenCalled();
    expect(webApp.expand).not.toHaveBeenCalled();
  });

  it("refuses to invent credentials when Telegram mode has no WebApp", async () => {
    const client = createTelegramClient({ mode: "telegram" });

    await expect(client.getInitData()).rejects.toThrow(
      "Telegram Mini App is unavailable",
    );
  });

  it("falls back to UTC when timezone lookup is empty or throws", () => {
    const empty = createTelegramClient({
      mode: "mock",
      mock: {
        createInitData: createDevInitData,
        firstName: getDevFirstName(),
      },
      resolveTimezone: () => "",
    });
    const broken = createTelegramClient({
      mode: "mock",
      mock: {
        createInitData: createDevInitData,
        firstName: getDevFirstName(),
      },
      resolveTimezone: () => {
        throw new Error("Intl unavailable");
      },
    });

    expect(empty.getTimezone()).toBe("UTC");
    expect(broken.getTimezone()).toBe("UTC");
  });
});
