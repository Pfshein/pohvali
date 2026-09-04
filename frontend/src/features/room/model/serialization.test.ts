import { describe, expect, it } from "vitest";

import { createStarterRoom } from "../catalog/starterRoom";
import { createRoomCatalog } from "../catalog/roomCatalog";
import { deserializeRoom, serializeRoom } from "./serialization";

describe("room serialization", () => {
  it("round-trips version one state", () => {
    const room = createStarterRoom("ava");

    expect(deserializeRoom(serializeRoom(room))).toEqual(room);
  });

  it("validates dynamic mascot templates against the supplied catalog", () => {
    const catalog = createRoomCatalog([{
      code: "sonya",
      label: "Соня",
      assetPath: "/api/v1/mascots/sonya/image",
    }]);
    const room = createStarterRoom("sonya", catalog);

    expect(deserializeRoom(serializeRoom(room), catalog)).toEqual(room);
  });

  it.each([
    '{"schemaVersion":2,"items":[]}',
    '{"schemaVersion":1,"items":[{"id":"same","templateId":"chair.basic","position":{"x":0.5,"y":0.7},"scale":1,"rotation":0,"layer":"furniture","zIndex":0,"zoneId":"floor","locked":false},{"id":"same","templateId":"chair.basic","position":{"x":0.5,"y":0.7},"scale":1,"rotation":0,"layer":"furniture","zIndex":0,"zoneId":"floor","locked":false}]}',
    '{"schemaVersion":1,"items":[{"id":"chair","templateId":"chair.basic","position":{"x":4,"y":0.7},"scale":1,"rotation":0,"layer":"furniture","zIndex":0,"zoneId":"floor","locked":false}]}',
  ])("rejects invalid persisted state", (json) => {
    expect(() => deserializeRoom(json)).toThrow("Invalid room state");
  });
});
