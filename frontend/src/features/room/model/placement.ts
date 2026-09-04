import {
  findRoomItem,
  type NormalizedPoint,
  type RoomItem,
  type RoomState,
  type RoomZoneId,
} from "./room";

/**
 * The floor starts where the wall ends; the value matches the approved mockup
 * where the border sits around 55–58% of the content height.
 */
export const ROOM_FLOOR_LINE = 0.56;

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

export function clampNormalizedPoint(point: NormalizedPoint): NormalizedPoint {
  return { x: clamp01(point.x), y: clamp01(point.y) };
}

function clampToZone(point: NormalizedPoint, zoneId: RoomZoneId): NormalizedPoint {
  const clamped = clampNormalizedPoint(point);
  if (zoneId === "wall") return { x: clamped.x, y: Math.min(clamped.y, ROOM_FLOOR_LINE) };
  if (zoneId === "floor") return { x: clamped.x, y: Math.max(clamped.y, ROOM_FLOOR_LINE) };
  return clamped;
}

export function isMovableItem(item: RoomItem): boolean {
  return !item.locked && item.zoneId !== "fixed";
}

/**
 * Fixed and locked items always keep their current point; everything else is
 * clamped to 0…1 and to its placement zone.
 */
export function resolvePlacement(item: RoomItem, candidate: NormalizedPoint): NormalizedPoint {
  if (!isMovableItem(item)) return item.position;
  return clampToZone(candidate, item.zoneId);
}

/** Returns a new state with one item moved; the input state is never mutated. */
export function moveRoomItem(state: RoomState, id: string, candidate: NormalizedPoint): RoomState {
  const item = findRoomItem(state, id);
  if (!item) return state;
  const position = resolvePlacement(item, candidate);
  if (position.x === item.position.x && position.y === item.position.y) return state;
  return {
    ...state,
    items: state.items.map((current) =>
      current.id === id ? { ...current, position } : current,
    ),
  };
}
