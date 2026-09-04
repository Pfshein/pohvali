import { describe, expect, it } from "vitest";

import { compareRoomItems, moveRoomItem, roomSortValue, type RoomState } from "./room";

describe("room model", () => {
  it("moves an item immutably and clamps it to its placement zone", () => {
    const state: RoomState = {
      schemaVersion: 1,
      items: [{
        id: "chair-1",
        templateId: "chair.basic",
        position: { x: 0.6, y: 0.8 },
        scale: 1,
        rotation: 0,
        layer: "furniture",
        zIndex: 2,
        zoneId: "floor",
        locked: false,
      }],
    };

    const moved = moveRoomItem(state, "chair-1", { x: 2, y: 0.1 });

    expect(moved.items[0]?.position).toEqual({ x: 0.92, y: 0.55 });
    expect(state.items[0]?.position).toEqual({ x: 0.6, y: 0.8 });
  });

  it("keeps local z-index inside a deterministic logical layer", () => {
    const furniture = roomSortValue({ layer: "furniture", zIndex: 999 });
    const mascot = roomSortValue({ layer: "mascot", zIndex: -999 });

    expect(furniture).toBeLessThan(mascot);
  });

  it("breaks equal layer and z-index ties by stable instance id", () => {
    const [item] = createItems();
    const later = { ...item!, id: "plant-z" };
    const earlier = { ...item!, id: "plant-a" };

    expect([later, earlier].sort(compareRoomItems).map(({ id }) => id)).toEqual([
      "plant-a",
      "plant-z",
    ]);
  });
});

function createItems(): RoomState["items"] {
  return [{
    id: "plant",
    templateId: "chair.basic",
    position: { x: 0.5, y: 0.7 },
    scale: 1,
    rotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId: "floor",
    locked: false,
  }];
}
