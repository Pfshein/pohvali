/**
 * Renderer-independent room model (PH-902 spec section 5). Coordinates are
 * normalized to the room viewport (0…1 on both axes), so resizing never
 * touches persisted state.
 */

export type NormalizedPoint = { x: number; y: number };
export type RoomZoneId = "wall" | "floor" | "fixed";
export type RoomLayer =
  | "background"
  | "wall"
  | "floor"
  | "furniture"
  | "mascot"
  | "foreground"
  | "effects";

export interface RoomItem {
  id: string;
  templateId: string;
  position: NormalizedPoint;
  scale: number;
  rotation: number;
  layer: RoomLayer;
  zIndex: number;
  zoneId: RoomZoneId;
  locked: boolean;
}

export interface RoomState {
  schemaVersion: 1;
  items: readonly RoomItem[];
}

/** The only signal a room renderer may send back in the first release. */
export type RoomItemMoveHandler = (id: string, position: NormalizedPoint) => void;

/** Layer bases are spaced 1000 apart so a local z-index can never cross layers. */
export const ROOM_LAYER_BASE: Record<RoomLayer, number> = {
  background: 0,
  wall: 1000,
  floor: 2000,
  furniture: 3000,
  mascot: 4000,
  foreground: 5000,
  effects: 6000,
};

export const ROOM_Z_INDEX_RANGE = { min: -499, max: 499 } as const;

const ROOM_LAYERS: readonly RoomLayer[] = [
  "background",
  "wall",
  "floor",
  "furniture",
  "mascot",
  "foreground",
  "effects",
];

export function isRoomLayer(value: unknown): value is RoomLayer {
  return typeof value === "string" && ROOM_LAYERS.includes(value as RoomLayer);
}

export function isRoomZoneId(value: unknown): value is RoomZoneId {
  return value === "wall" || value === "floor" || value === "fixed";
}

export function compareRoomItems(left: RoomItem, right: RoomItem): number {
  const base = ROOM_LAYER_BASE[left.layer] - ROOM_LAYER_BASE[right.layer];
  if (base !== 0) return base;
  if (left.zIndex !== right.zIndex) return left.zIndex - right.zIndex;
  return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
}

export function sortRoomItems(items: readonly RoomItem[]): readonly RoomItem[] {
  return [...items].sort(compareRoomItems);
}

export function findRoomItem(state: RoomState, id: string): RoomItem | undefined {
  return state.items.find((item) => item.id === id);
}
