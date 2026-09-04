import { describe, expect, it } from "vitest";

import { createRoomCatalog, type RoomMascotAsset } from "../catalog/roomCatalog";
import { createStarterRoom } from "../catalog/starterRoom";
import { planScene, type SceneView } from "./scenePlan";

const mira: RoomMascotAsset = {
  code: "mira",
  name: "Кошка Мира",
  assetPath: "/assets/mascots/mira.png",
};

const view: SceneView = { width: 390, height: 844 };

describe("scene plan", () => {
  it("orders the seated composition chair back → mascot → chair front", () => {
    const catalog = createRoomCatalog([mira]);
    const plan = planScene(createStarterRoom(mira, catalog), catalog, view);

    expect(plan.sprites.map((sprite) => sprite.id)).toEqual([
      "seat-back",
      "active-mascot",
      "seat-front",
    ]);
  });

  it("places every starter sprite inside the viewport with positive size", () => {
    const catalog = createRoomCatalog([mira]);
    const plan = planScene(createStarterRoom(mira, catalog), catalog, view);

    for (const sprite of plan.sprites) {
      expect(sprite.width).toBeGreaterThan(0);
      expect(sprite.height).toBeGreaterThan(0);
      expect(sprite.x).toBeGreaterThanOrEqual(0);
      expect(sprite.x).toBeLessThanOrEqual(view.width);
      expect(sprite.y).toBeGreaterThanOrEqual(0);
      expect(sprite.y).toBeLessThanOrEqual(view.height);
      expect(sprite.anchor.x).toBeGreaterThan(0);
      expect(sprite.anchor.x).toBeLessThan(1);
      expect(sprite.anchor.y).toBeGreaterThan(0);
      expect(sprite.anchor.y).toBeLessThanOrEqual(1);
    }
  });

  it("seats the mascot on the chair cushion rather than on the chair's floor line", () => {
    const catalog = createRoomCatalog([mira]);
    const plan = planScene(createStarterRoom(mira, catalog), catalog, view);
    const [chairBack, mascot] = plan.sprites;

    const chairTop = chairBack!.y - chairBack!.anchor.y * chairBack!.height;
    const chairFloor = chairBack!.y + (1 - chairBack!.anchor.y) * chairBack!.height;
    const mascotTop = mascot!.y - mascot!.anchor.y * mascot!.height;
    const mascotBase = mascot!.y + (1 - mascot!.anchor.y) * mascot!.height;

    // Sharing the chair's anchor drops the character to the floor line, where
    // the front cushion buries it. Its base belongs on the seat.
    expect(mascot!.y).toBeLessThan(chairBack!.y);
    expect(mascotBase).toBeLessThan(chairFloor);
    // …and its head stays inside the backrest instead of rising above it.
    expect(mascotTop).toBeGreaterThan(chairTop);
  });

  it("resolves texture sources from the catalog and falls back calmly when missing", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);

    const withTextures = planScene(room, catalog, view);
    expect(withTextures.sprites.map((sprite) => sprite.src)).toEqual([
      "/assets/room/v2/chair-back.webp",
      "/assets/mascots/mira.png",
      "/assets/room/v2/chair-front.webp",
    ]);
    expect(withTextures.sprites.every((sprite) => !sprite.placeholder)).toBe(true);

    // A catalog without the mascot template (e.g. desynced state) plans a
    // neutral placeholder instead of throwing or blanking the room.
    const emptyCatalog = createRoomCatalog([]);
    const degraded = planScene(room, emptyCatalog, view);
    expect(degraded.sprites.find((sprite) => sprite.id === "active-mascot")?.placeholder)
      .toBe(true);
    expect(degraded.sprites.find((sprite) => sprite.id === "seat-back")?.src)
      .toBe("/assets/room/v2/chair-back.webp");
  });

  it("scales the plan with the viewport without changing normalized anchors", () => {
    const catalog = createRoomCatalog([mira]);
    const room = createStarterRoom(mira, catalog);

    const tall = planScene(room, catalog, view);
    const short = planScene(room, catalog, { width: 360, height: 667 });

    expect(short.sprites[0]!.width).toBeLessThan(tall.sprites[0]!.width);
    expect(short.sprites.map((sprite) => sprite.anchor)).toEqual(
      tall.sprites.map((sprite) => sprite.anchor),
    );
  });
});
