import { describe, expect, it } from "vitest";

import { clampNormalizedPoint, isMovableItem, resolvePlacement } from "./placement";
import type { RoomItem } from "./room";

function item(zoneId: RoomItem["zoneId"], overrides: Partial<RoomItem> = {}): RoomItem {
  return {
    id: "item",
    templateId: "plant.small",
    position: { x: 0.5, y: 0.75 },
    scale: 1,
    rotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId,
    locked: false,
    ...overrides,
  };
}

describe("placement zones", () => {
  it("clamps coordinates into 0…1 without mutating the input", () => {
    const point = { x: -0.4, y: 1.7 };
    const clamped = clampNormalizedPoint(point);

    expect(clamped).toEqual({ x: 0, y: 1 });
    expect(point).toEqual({ x: -0.4, y: 1.7 });
    expect(clampNormalizedPoint({ x: 0.25, y: 0.5 })).toEqual({ x: 0.25, y: 0.5 });
  });

  it("keeps wall items above the floor line and floor items below it", () => {
    const wall = resolvePlacement(item("wall"), { x: 0.4, y: 0.95 });
    expect(wall.y).toBeLessThanOrEqual(0.56);

    const floor = resolvePlacement(item("floor"), { x: 0.4, y: 0.05 });
    expect(floor.y).toBeGreaterThanOrEqual(0.56);

    expect(wall.x).toBe(0.4);
    expect(floor.x).toBe(0.4);
  });

  it("returns the original point for fixed or locked items", () => {
    const original = { x: 0.5, y: 0.73 };
    const fixed = item("fixed", { position: original });
    const locked = item("floor", { position: original, locked: true });

    expect(resolvePlacement(fixed, { x: 0.1, y: 0.1 })).toEqual(original);
    expect(resolvePlacement(locked, { x: 0.1, y: 0.1 })).toEqual(original);
  });

  it("marks only unlocked non-fixed items as movable", () => {
    expect(isMovableItem(item("wall"))).toBe(true);
    expect(isMovableItem(item("floor"))).toBe(true);
    expect(isMovableItem(item("fixed"))).toBe(false);
    expect(isMovableItem(item("floor", { locked: true }))).toBe(false);
  });
});
