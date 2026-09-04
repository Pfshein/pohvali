import { describe, expect, it } from "vitest";

import { parseRoomState } from "../model/serialization";
import { createRoomCatalog, instantiateRoomItem, type RoomMascotAsset } from "./roomCatalog";
import { createStarterRoom, ROOM_SEAT_ANCHOR } from "./starterRoom";

const mira: RoomMascotAsset = {
  code: "mira",
  name: "Кошка Мира",
  assetPath: "/assets/mascots/mira.png",
};

describe("room catalog", () => {
  it("builds the starter seated composition from registered instances", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);
    expect(room.items.map((item) => [item.templateId, item.layer])).toEqual([
      ["chair.basic.back", "furniture"],
      ["mascot.mira", "mascot"],
      ["chair.basic.front", "foreground"],
    ]);
  });

  it("seats every starter item at one shared locked anchor", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);

    expect(ROOM_SEAT_ANCHOR).toEqual({ x: 0.5, y: 0.73 });
    for (const item of room.items) {
      expect(item.position).toEqual(ROOM_SEAT_ANCHOR);
      expect(item.locked).toBe(true);
      expect(item.zoneId).toBe("fixed");
      expect(item.rotation).toBe(0);
    }
    expect(room.schemaVersion).toBe(1);
  });

  it("gives every starter item its own position object", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);
    const positions = room.items.map((item) => item.position);

    // Equal values, independent instances: no item may alias the shared
    // constant or another item, or moving one would move its neighbours.
    for (const position of positions) {
      expect(position).not.toBe(ROOM_SEAT_ANCHOR);
    }
    expect(new Set(positions).size).toBe(room.items.length);
  });

  it("registers the active mascot from supplied data, never a hardcoded list", () => {
    const adminMascot: RoomMascotAsset = {
      code: "ufo-77",
      name: "НЛО",
      assetPath: "/assets/mascots/admin/ufo-77.webp",
    };
    const catalog = createRoomCatalog([adminMascot]);

    const template = catalog.templates.get("mascot.ufo-77");
    expect(template).toBeDefined();
    expect(template?.assets).toEqual([
      { kind: "texture", src: "/assets/mascots/admin/ufo-77.webp" },
    ]);

    const room = createStarterRoom(adminMascot, catalog);
    expect(room.items.map((item) => item.templateId)).toContain("mascot.ufo-77");
  });

  it("registers the split chair templates with their manifest assets", () => {
    const catalog = createRoomCatalog([mira]);

    expect(catalog.templates.get("chair.basic.back")).toMatchObject({
      layer: "furniture",
      zoneId: "fixed",
      assets: [{ kind: "texture", src: "/assets/room/v2/chair-back.webp" }],
    });
    expect(catalog.templates.get("chair.basic.front")).toMatchObject({
      layer: "foreground",
      zoneId: "fixed",
      assets: [{ kind: "texture", src: "/assets/room/v2/chair-front.webp" }],
    });
  });

  it("round-trips the starter room through the versioned parser", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);

    const serialized = JSON.stringify(room);
    expect(parseRoomState(serialized, catalog)).toEqual({ ok: true, state: room });
  });

  it("instantiates independent items from one template", () => {
    const catalog = createRoomCatalog([mira]);

    const left = instantiateRoomItem(catalog, "mascot.mira", {
      id: "mascot-left",
      position: { x: 0.25, y: 0.8 },
    });
    const right = instantiateRoomItem(catalog, "mascot.mira", {
      id: "mascot-right",
      position: { x: 0.75, y: 0.8 },
    });

    expect(left.id).not.toBe(right.id);
    expect(left.position).not.toEqual(right.position);
    expect(catalog.has("mascot.mira")).toBe(true);
    expect(catalog.has("mascot.pol")).toBe(false);
  });

  it("rejects instantiating an unknown template", () => {
    const catalog = createRoomCatalog([mira]);

    expect(() =>
      instantiateRoomItem(catalog, "mascot.unknown", {
        id: "x",
        position: { x: 0.5, y: 0.5 },
      }),
    ).toThrow(/unknown room template/i);
  });
});
