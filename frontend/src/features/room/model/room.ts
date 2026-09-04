import { clampToZone, type NormalizedPoint, type RoomZoneId } from "./placement";

export const ROOM_SCHEMA_VERSION = 1 as const;

export const ROOM_LAYER_BASE = {
  background: 0,
  wall: 1_000,
  floor: 2_000,
  furniture: 3_000,
  mascot: 4_000,
  foreground: 5_000,
  effects: 6_000,
} as const;

export type RoomLayer = keyof typeof ROOM_LAYER_BASE;

export interface RoomItem {
  readonly id: string;
  readonly templateId: string;
  readonly position: NormalizedPoint;
  readonly scale: number;
  readonly rotation: number;
  readonly layer: RoomLayer;
  readonly zIndex: number;
  readonly zoneId: RoomZoneId;
  readonly locked: boolean;
}

export interface RoomState {
  readonly schemaVersion: typeof ROOM_SCHEMA_VERSION;
  readonly items: readonly RoomItem[];
}

function localZIndex(value: number): number {
  return Math.min(499, Math.max(-499, Math.trunc(value)));
}

export function roomSortValue(item: Pick<RoomItem, "layer" | "zIndex">): number {
  return ROOM_LAYER_BASE[item.layer] + localZIndex(item.zIndex);
}

export function compareRoomItems(
  left: Pick<RoomItem, "id" | "layer" | "zIndex">,
  right: Pick<RoomItem, "id" | "layer" | "zIndex">,
): number {
  const byLayerAndZ = roomSortValue(left) - roomSortValue(right);
  if (byLayerAndZ !== 0) return byLayerAndZ;
  return left.id < right.id ? -1 : left.id > right.id ? 1 : 0;
}

export function moveRoomItem(
  state: RoomState,
  id: string,
  position: NormalizedPoint,
): RoomState {
  let changed = false;
  const items = state.items.map((item) => {
    if (item.id !== id || item.locked) return item;
    changed = true;
    return { ...item, position: clampToZone(position, item.zoneId) };
  });
  return changed ? { ...state, items } : state;
}
