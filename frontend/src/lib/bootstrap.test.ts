import { describe, expect, it, vi } from "vitest";

import { createAppBootstrap } from "./bootstrap";

describe("app bootstrap", () => {
  it("reaches ready when session and key both succeed", async () => {
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      { openSession: vi.fn(async () => {}), ensureKey: vi.fn(async () => {}) },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "ready"]);
  });

  it("stops at session-error and never runs the key step", async () => {
    const ensureKey = vi.fn(async () => {});
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      {
        openSession: vi.fn(async () => {
          throw new Error("offline");
        }),
        ensureKey,
      },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "session-error"]);
    expect(ensureKey).not.toHaveBeenCalled();
  });

  it("reports storage-error when the key step throws", async () => {
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      {
        openSession: vi.fn(async () => {}),
        ensureKey: vi.fn(async () => {
          throw new Error("no cloud storage");
        }),
      },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();

    expect(phases).toEqual(["loading", "storage-error"]);
  });

  it("recovers on a later retry", async () => {
    const openSession = vi
      .fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(undefined);
    const phases: string[] = [];
    const bootstrap = createAppBootstrap(
      { openSession, ensureKey: vi.fn(async () => {}) },
      (phase) => phases.push(phase),
    );

    await bootstrap.connect();
    await bootstrap.connect();

    expect(phases).toEqual(["loading", "session-error", "loading", "ready"]);
  });
});
