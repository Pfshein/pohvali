import { describe, expect, it } from "vitest";

import { createRoomCatalog, instantiateRoomItem } from "./roomCatalog";
import { createStarterRoom } from "./starterRoom";

describe("room catalog", () => {
  it("creates independent instances from one template", () => {
    const first = instantiateRoomItem("chair.basic", "chair-1");
    const second = instantiateRoomItem("chair.basic", "chair-2", {
      position: { x: 0.3, y: 0.7 },
    });

    expect(first.id).toBe("chair-1");
    expect(second.id).toBe("chair-2");
    expect(first.templateId).toBe(second.templateId);
    expect(first.position).not.toEqual(second.position);
  });

  it("creates a starter room with a chair and the active mascot", () => {
    const room = createStarterRoom("mira");

    expect(room.items.map((item) => item.templateId)).toEqual([
      "chair.basic",
      "mascot.mira",
    ]);
  });

  it("uses authoritative metadata for an admin-added mascot", () => {
    const mascot = {
      code: "sonya",
      label: "Соня",
      assetPath: "/api/v1/mascots/sonya/image",
    };
    const catalog = createRoomCatalog([mascot]);
    const room = createStarterRoom(mascot.code, catalog);

    expect(room.items[1]?.templateId).toBe("mascot.sonya");
    expect(catalog.assets["mascot.sonya"]).toEqual({
      kind: "texture",
      src: mascot.assetPath,
    });
  });
});
