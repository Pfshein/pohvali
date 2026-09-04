import type { NormalizedPoint, RoomState } from "../model/room";
import { instantiateRoomItem, type RoomCatalog, type RoomMascotAsset } from "./roomCatalog";

/**
 * Shared anchor for the locked base composition: chair back, active mascot
 * and chair front are separate instances placed at one point, ordered by
 * their layers. Exact scale is tuned in the renderer, not here.
 */
export const ROOM_SEAT_ANCHOR: NormalizedPoint = { x: 0.5, y: 0.73 };

export const CHAIR_BACK_INSTANCE_ID = "seat-back";
export const ACTIVE_MASCOT_INSTANCE_ID = "active-mascot";
export const CHAIR_FRONT_INSTANCE_ID = "seat-front";

export function createStarterRoom(
  activeMascot: RoomMascotAsset,
  catalog: RoomCatalog,
): RoomState {
  return {
    schemaVersion: 1,
    items: [
      instantiateRoomItem(catalog, "chair.basic.back", {
        id: CHAIR_BACK_INSTANCE_ID,
        position: { ...ROOM_SEAT_ANCHOR },
      }),
      instantiateRoomItem(catalog, `mascot.${activeMascot.code}`, {
        id: ACTIVE_MASCOT_INSTANCE_ID,
        position: { ...ROOM_SEAT_ANCHOR },
      }),
      instantiateRoomItem(catalog, "chair.basic.front", {
        id: CHAIR_FRONT_INSTANCE_ID,
        position: { ...ROOM_SEAT_ANCHOR },
      }),
    ],
  };
}
