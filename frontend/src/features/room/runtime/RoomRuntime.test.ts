import { describe, expect, it, vi } from "vitest";

import { createStarterRoom } from "../catalog/starterRoom";
import { RoomRuntime, type RoomRenderer } from "./RoomRuntime";

function renderer() {
  return {
    mount: vi.fn<RoomRenderer["mount"]>(async () => undefined),
    update: vi.fn(),
    resize: vi.fn(),
    setEditing: vi.fn(),
    destroy: vi.fn(),
  };
}

describe("RoomRuntime", () => {
  it("forwards the lifecycle to one renderer in order", async () => {
    const target = renderer();
    const runtime = new RoomRuntime(target);
    const room = createStarterRoom("ava");
    const host = {} as HTMLElement;

    await runtime.mount(host, room);
    runtime.update(room);
    runtime.resize(390, 720);
    runtime.setEditing(true);
    runtime.destroy();

    expect(target.mount).toHaveBeenCalledWith(host, room);
    expect(target.update).toHaveBeenCalledWith(room);
    expect(target.resize).toHaveBeenCalledWith(390, 720);
    expect(target.setEditing).toHaveBeenCalledWith(true);
    expect(target.destroy).toHaveBeenCalledOnce();
  });

  it("destroys once and ignores work after disposal", async () => {
    const target = renderer();
    const runtime = new RoomRuntime(target);
    runtime.destroy();
    runtime.destroy();

    await runtime.mount({} as HTMLElement, createStarterRoom("ava"));
    runtime.update(createStarterRoom("ava"));
    runtime.resize(1, 1);
    runtime.setEditing(true);

    expect(target.destroy).toHaveBeenCalledOnce();
    expect(target.mount).not.toHaveBeenCalled();
    expect(target.update).not.toHaveBeenCalled();
    expect(target.resize).not.toHaveBeenCalled();
    expect(target.setEditing).not.toHaveBeenCalled();
  });

  it("queues updates and resize until asynchronous mount completes", async () => {
    let finishMount: (() => void) | undefined;
    const target = renderer();
    target.mount.mockImplementation(() => new Promise<void>((resolve) => {
      finishMount = resolve;
    }));
    const runtime = new RoomRuntime(target);
    const nextRoom = createStarterRoom("mira");

    const mounting = runtime.mount({} as HTMLElement, createStarterRoom("ava"));
    runtime.update(nextRoom);
    runtime.resize(412, 732);
    runtime.setEditing(true);

    expect(target.update).not.toHaveBeenCalled();
    expect(target.resize).not.toHaveBeenCalled();
    expect(target.setEditing).not.toHaveBeenCalled();

    finishMount?.();
    await mounting;

    expect(target.update).toHaveBeenCalledWith(nextRoom);
    expect(target.resize).toHaveBeenCalledWith(412, 732);
    expect(target.setEditing).toHaveBeenCalledWith(true);
  });
});
