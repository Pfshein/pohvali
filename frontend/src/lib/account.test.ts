import { describe, expect, it, vi } from "vitest";

import type { TelegramClient } from "./telegram";
import { deleteAccountData, nextDeletionStep } from "./account";

function fakeTelegramClient(): TelegramClient {
  return {
    mode: "telegram",
    initialize() {},
    getInitData: async () => "query_id=raw%2Bvalue&hash=trusted",
    getFirstName: () => undefined,
    getTimezone: () => "Europe/Moscow",
  };
}

describe("account deletion transport", () => {
  it("sends an authorized DELETE without any body", async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 204 }));

    await deleteAccountData(fakeTelegramClient(), fetcher);

    expect(fetcher).toHaveBeenCalledWith("/api/v1/session", {
      method: "DELETE",
      headers: {
        Authorization: "tma query_id=raw%2Bvalue&hash=trusted",
      },
    });
  });

  it("returns a generic error without exposing the response body", async () => {
    const fetcher = vi.fn(async () => new Response(
      "sensitive upstream detail",
      { status: 401 },
    ));

    await expect(deleteAccountData(fakeTelegramClient(), fetcher)).rejects.toThrow(
      "Could not delete account data",
    );
  });
});

describe("deletion step machine", () => {
  it("requires an explicit confirm before working state", () => {
    expect(nextDeletionStep("idle", "request")).toBe("confirm");
    expect(nextDeletionStep("confirm", "confirm")).toBe("working");
    expect(nextDeletionStep("confirm", "cancel")).toBe("idle");
  });

  it("does not allow starting deletion straight from idle", () => {
    expect(nextDeletionStep("idle", "confirm")).toBe("idle");
  });

  it("ignores accidental events while working or after completion", () => {
    expect(nextDeletionStep("working", "request")).toBe("working");
    expect(nextDeletionStep("working", "confirm")).toBe("working");
    expect(nextDeletionStep("done", "request")).toBe("done");
    expect(nextDeletionStep("done", "confirm")).toBe("done");
  });

  it("recovers from an error only through a new explicit request", () => {
    expect(nextDeletionStep("working", "failed")).toBe("error");
    expect(nextDeletionStep("error", "request")).toBe("confirm");
    expect(nextDeletionStep("error", "confirm")).toBe("error");
  });
});
