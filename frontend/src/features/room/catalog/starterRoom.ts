import type { RoomState } from "../model/room";
import {
  DEFAULT_ROOM_CATALOG,
  hasRoomTemplate,
  instantiateRoomItem,
  type RoomCatalog,
} from "./roomCatalog";

const FALLBACK_MASCOT = "ava";

export function createStarterRoom(
  mascotCode: string,
  catalog: RoomCatalog = DEFAULT_ROOM_CATALOG,
): RoomState {
  const mascotTemplate = `mascot.${mascotCode}`;
  const safeMascotTemplate = hasRoomTemplate(mascotTemplate, catalog)
    ? mascotTemplate
    : `mascot.${FALLBACK_MASCOT}`;
  if (!hasRoomTemplate(safeMascotTemplate, catalog)) {
    throw new Error(`Unknown starter mascot: ${mascotCode}`);
  }
  return {
    schemaVersion: 1,
    items: [
      instantiateRoomItem("chair.basic", "starter-chair", {}, catalog),
      instantiateRoomItem(safeMascotTemplate, "active-mascot", {}, catalog),
    ],
  };
}
