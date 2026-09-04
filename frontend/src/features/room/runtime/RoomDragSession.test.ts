import { describe, expect, it, vi } from "vitest";

import { RoomDragSession } from "./RoomDragSession";
import type { RoomItem } from "../model/room";

function plant(overrides: Partial<RoomItem> = {}): RoomItem {
  return {
    id: "plant",
    templateId: "plant.small",
    position: { x: 0.5, y: 0.75 },
    scale: 1,
    rotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId: "floor",
    locked: false,
    ...overrides,
  };
}

function createSession() {
  const onPreview = vi.fn();
  const onCommit = vi.fn();
  const onCancel = vi.fn();
  const session = new RoomDragSession({ onPreview, onCommit, onCancel });
  return { session, onPreview, onCommit, onCancel };
}

describe("RoomDragSession", () => {
  it("accepts only the first active pointer", () => {
    const { session, onPreview } = createSession();

    expect(session.begin(plant(), { pointerId: 1, x: 0.5, y: 0.75 })).toBe(true);
    expect(session.begin(plant(), { pointerId: 2, x: 0.2, y: 0.2 })).toBe(false);

    session.move({ pointerId: 2, x: 0.1, y: 0.1 });
    expect(onPreview).not.toHaveBeenCalled();

    session.move({ pointerId: 1, x: 0.6, y: 0.8 });
    expect(onPreview).toHaveBeenCalledWith("plant", { x: 0.6, y: 0.8 });
  });

  it("keeps the grab offset so the item does not jump to the pointer", () => {
    const { session, onPreview } = createSession();
    session.begin(plant(), { pointerId: 1, x: 0.55, y: 0.78 });

    session.move({ pointerId: 1, x: 0.65, y: 0.88 });

    expect(onPreview).toHaveBeenCalledWith("plant", { x: 0.6, y: 0.85 });
  });

  it("clamps previews through the placement zone", () => {
    const { session, onPreview } = createSession();
    const wallItem = plant({ zoneId: "wall", position: { x: 0.3, y: 0.2 } });
    session.begin(wallItem, { pointerId: 1, x: 0.31, y: 0.21 });

    session.move({ pointerId: 1, x: 0.4, y: 0.95 });

    expect(onPreview).toHaveBeenCalledWith("plant", { x: 0.39, y: 0.56 });
  });

  it("commits the last preview on the matching pointerup only", () => {
    const { session, onCommit } = createSession();
    session.begin(plant(), { pointerId: 1, x: 0.5, y: 0.75 });
    session.move({ pointerId: 1, x: 0.62, y: 0.8 });

    session.end({ pointerId: 2, x: 0.9, y: 0.9 });
    expect(onCommit).not.toHaveBeenCalled();

    session.end({ pointerId: 1, x: 0.62, y: 0.8 });
    expect(onCommit).toHaveBeenCalledWith("plant", { x: 0.62, y: 0.8 });
  });

  it("restores the last committed point on pointercancel or window blur", () => {
    const { session, onCommit, onCancel } = createSession();
    session.begin(plant(), { pointerId: 1, x: 0.5, y: 0.75 });
    session.move({ pointerId: 1, x: 0.62, y: 0.8 });

    session.cancel();

    expect(onCommit).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledWith("plant");

    // A late pointerup from the cancelled gesture must not commit anything.
    session.end({ pointerId: 1, x: 0.62, y: 0.8 });
    expect(onCommit).not.toHaveBeenCalled();
  });

  it("ignores moves and ends when no drag is active", () => {
    const { session, onPreview, onCommit, onCancel } = createSession();

    session.move({ pointerId: 1, x: 0.6, y: 0.8 });
    session.end({ pointerId: 1, x: 0.6, y: 0.8 });
    session.cancel();

    expect(onPreview).not.toHaveBeenCalled();
    expect(onCommit).not.toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });
});
