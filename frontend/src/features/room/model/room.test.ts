import { describe, expect, it } from "vitest";

import {
  compareRoomItems,
  ROOM_LAYER_BASE,
  ROOM_Z_INDEX_RANGE,
  type RoomItem,
  type RoomState,
} from "./room";
import { moveRoomItem } from "./placement";

function chairBack(id: string, overrides: Partial<RoomItem> = {}): RoomItem {
  return {
    id,
    templateId: "chair.basic.back",
    position: { x: 0.5, y: 0.73 },
    scale: 1,
    rotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId: "fixed",
    locked: true,
    ...overrides,
  };
}

describe("room model", () => {
  it("keeps two instances of one template independent", () => {
    const state: RoomState = {
      schemaVersion: 1,
      items: [
        chairBack("plant-a", { position: { x: 0.2, y: 0.8 }, zoneId: "floor", locked: false }),
        chairBack("plant-b", { position: { x: 0.7, y: 0.6 }, zoneId: "floor", locked: false }),
      ],
    };

    const moved = moveRoomItem(state, "plant-a", { x: 0.3, y: 0.85 });

    expect(moved).not.toBe(state);
    expect(moved.items[0]).not.toBe(state.items[0]);
    expect(moved.items[0]!.position).toEqual({ x: 0.3, y: 0.85 });
    expect(moved.items[1]).toBe(state.items[1]);
    expect(state.items[0]!.position).toEqual({ x: 0.2, y: 0.8 });
  });

  it("sorts deterministically by layer base then local z-index then id", () => {
    const items: RoomItem[] = [
      chairBack("chair-front", { layer: "foreground", zIndex: 10 }),
      chairBack("mascot-x", { layer: "mascot", zIndex: -10, templateId: "mascot.x" }),
      chairBack("chair-back-2", { layer: "furniture", zIndex: 5 }),
      chairBack("chair-back-1", { layer: "furniture", zIndex: 5 }),
      chairBack("rug", { layer: "floor", zIndex: 0 }),
    ];

    expect([...items].sort(compareRoomItems).map((item) => item.layer)).toEqual([
      "floor",
      "furniture",
      "furniture",
      "mascot",
      "foreground",
    ]);
    expect([...items].sort(compareRoomItems).map((item) => item.id)).toEqual([
      "rug",
      "chair-back-1",
      "chair-back-2",
      "mascot-x",
      "chair-front",
    ]);
  });

  it("spreads layer bases far apart and clamps local z-index inside a layer", () => {
    const order = Object.values(ROOM_LAYER_BASE);
    for (let index = 1; index < order.length; index += 1) {
      expect(order[index]! - order[index - 1]!).toBeGreaterThanOrEqual(1000);
    }
    // A local z-index at its maximum cannot jump into the next layer.
    expect(ROOM_LAYER_BASE.furniture! + ROOM_Z_INDEX_RANGE.max)
      .toBeLessThan(ROOM_LAYER_BASE.mascot! + ROOM_Z_INDEX_RANGE.min);
  });

  it("keeps every layer base larger than the previous surface layers", () => {
    expect(ROOM_LAYER_BASE.background).toBeLessThan(ROOM_LAYER_BASE.wall!);
    expect(ROOM_LAYER_BASE.wall!).toBeLessThan(ROOM_LAYER_BASE.floor!);
    expect(ROOM_LAYER_BASE.floor!).toBeLessThan(ROOM_LAYER_BASE.furniture!);
    expect(ROOM_LAYER_BASE.mascot!).toBeLessThan(ROOM_LAYER_BASE.foreground!);
    expect(ROOM_LAYER_BASE.foreground!).toBeLessThan(ROOM_LAYER_BASE.effects!);
  });
});
