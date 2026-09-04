import { describe, expect, it, vi } from "vitest";

import { RoomRuntime, type RoomRenderer } from "./RoomRuntime";
import type { RoomState } from "../model/room";

function state(): RoomState {
  return {
    schemaVersion: 1,
    items: [{
      id: "seat-back",
      templateId: "chair.basic.back",
      position: { x: 0.5, y: 0.73 },
      scale: 1,
      rotation: 0,
      layer: "furniture",
      zIndex: 0,
      zoneId: "fixed",
      locked: true,
    }],
  };
}

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

function createRenderer() {
  const mocks = {
    mount: vi.fn((): Promise<void> => Promise.resolve()),
    update: vi.fn(),
    resize: vi.fn(),
    setEditing: vi.fn(),
    destroy: vi.fn(),
  };
  const renderer: RoomRenderer = mocks;
  return { renderer, mocks };
}

describe("RoomRuntime", () => {
  it("applies update, resize and setEditing queued during an async mount in order", async () => {
    const { renderer, mocks } = createRenderer();
    const pending = deferred<void>();
    renderer.mount = vi.fn(() => pending.promise);
    const runtime = new RoomRuntime(renderer);
    const host = {} as HTMLElement;
    const room = state();

    const mounted = runtime.mount(host, room);
    runtime.update(room);
    runtime.resize(390, 844);
    runtime.setEditing(true);

    expect(renderer.update).not.toHaveBeenCalled();
    expect(renderer.resize).not.toHaveBeenCalled();
    expect(renderer.setEditing).not.toHaveBeenCalled();

    pending.resolve();
    await mounted;

    expect(renderer.mount).toHaveBeenCalledWith(host, room);
    expect(renderer.update).toHaveBeenCalledWith(room);
    expect(renderer.resize).toHaveBeenCalledWith(390, 844);
    expect(renderer.setEditing).toHaveBeenCalledWith(true);
    expect(mocks.update.mock.invocationCallOrder[0]!)
      .toBeLessThan(mocks.resize.mock.invocationCallOrder[0]!);
    expect(mocks.resize.mock.invocationCallOrder[0]!)
      .toBeLessThan(mocks.setEditing.mock.invocationCallOrder[0]!);
  });

  it("forwards live operations after mount completes", async () => {
    const { renderer } = createRenderer();
    const runtime = new RoomRuntime(renderer);
    await runtime.mount({} as HTMLElement, state());

    runtime.update(state());
    runtime.resize(360, 667);
    runtime.setEditing(false);

    expect(renderer.update).toHaveBeenCalledTimes(1);
    expect(renderer.resize).toHaveBeenCalledWith(360, 667);
    expect(renderer.setEditing).toHaveBeenCalledWith(false);
  });

  it("destroys the renderer exactly once even if destroy repeats or mount resolves late", async () => {
    const { renderer } = createRenderer();
    const pending = deferred<void>();
    renderer.mount = vi.fn(() => pending.promise);
    const runtime = new RoomRuntime(renderer);
    const room = state();

    const mounted = runtime.mount({} as HTMLElement, room);
    runtime.update(room); // queued while mounting
    runtime.destroy();
    runtime.destroy();

    pending.resolve();
    await mounted;

    expect(renderer.update).not.toHaveBeenCalled();
    expect(renderer.destroy).toHaveBeenCalledTimes(1);
  });

  it("absorbs a failed mount instead of rejecting into an unhandled promise", async () => {
    const { renderer } = createRenderer();
    renderer.mount = vi.fn(() => Promise.reject(new Error("WebGL unavailable")));
    const runtime = new RoomRuntime(renderer);

    await expect(runtime.mount({} as HTMLElement, state())).resolves.toBeUndefined();
  });

  it("releases the renderer that failed to mount and stays inert afterwards", async () => {
    const { renderer } = createRenderer();
    renderer.mount = vi.fn(() => Promise.reject(new Error("WebGL unavailable")));
    const runtime = new RoomRuntime(renderer);
    const room = state();

    const mounted = runtime.mount({} as HTMLElement, room);
    runtime.update(room); // queued while the doomed mount is in flight
    await mounted;

    runtime.resize(390, 844);
    runtime.setEditing(true);

    expect(renderer.destroy).toHaveBeenCalledTimes(1);
    expect(renderer.update).not.toHaveBeenCalled();
    expect(renderer.resize).not.toHaveBeenCalled();
    expect(renderer.setEditing).not.toHaveBeenCalled();
  });

  it("destroys a failed renderer only once when destroy also runs", async () => {
    const { renderer } = createRenderer();
    renderer.mount = vi.fn(() => Promise.reject(new Error("WebGL unavailable")));
    const runtime = new RoomRuntime(renderer);

    await runtime.mount({} as HTMLElement, state());
    runtime.destroy();

    expect(renderer.destroy).toHaveBeenCalledTimes(1);
  });

  it("keeps the state object untouched by resize", async () => {
    const { renderer } = createRenderer();
    const runtime = new RoomRuntime(renderer);
    const room = state();
    const snapshot = JSON.stringify(room);

    await runtime.mount({} as HTMLElement, room);
    runtime.resize(390, 844);
    runtime.resize(320, 568);

    expect(JSON.stringify(room)).toBe(snapshot);
  });

  it("survives a StrictMode mount → cleanup → mount sequence", async () => {
    const first = createRenderer();
    const firstPending = deferred<void>();
    first.renderer.mount = vi.fn(() => firstPending.promise);
    const firstRuntime = new RoomRuntime(first.renderer);
    const room = state();

    const firstMount = firstRuntime.mount({} as HTMLElement, room);
    firstRuntime.destroy(); // StrictMode cleanup while mounting

    const second = createRenderer();
    const secondRuntime = new RoomRuntime(second.renderer);

    const secondMount = secondRuntime.mount({} as HTMLElement, room);
    firstPending.resolve();
    await Promise.all([firstMount, secondMount]);

    secondRuntime.update(room);

    expect(first.renderer.destroy).toHaveBeenCalledTimes(1);
    expect(second.renderer.update).toHaveBeenCalledWith(room);
    expect(second.renderer.destroy).not.toHaveBeenCalled();
  });
});
