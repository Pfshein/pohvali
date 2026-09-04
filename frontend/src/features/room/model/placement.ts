export type NormalizedPoint = Readonly<{ x: number; y: number }>;
export type RoomZoneId = "wall" | "floor" | "fixed";

export interface PlacementZone {
  readonly id: RoomZoneId;
  readonly minX: number;
  readonly maxX: number;
  readonly minY: number;
  readonly maxY: number;
}

export const ROOM_PLACEMENT_ZONES: Readonly<Record<RoomZoneId, PlacementZone>> = {
  wall: { id: "wall", minX: 0.05, maxX: 0.95, minY: 0.08, maxY: 0.52 },
  floor: { id: "floor", minX: 0.08, maxX: 0.92, minY: 0.55, maxY: 0.94 },
  fixed: { id: "fixed", minX: 0, maxX: 1, minY: 0, maxY: 1 },
};

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export function clampToZone(point: NormalizedPoint, zoneId: RoomZoneId): NormalizedPoint {
  const zone = ROOM_PLACEMENT_ZONES[zoneId];
  return {
    x: clamp(point.x, zone.minX, zone.maxX),
    y: clamp(point.y, zone.minY, zone.maxY),
  };
}

export function screenToNormalized(
  point: Readonly<{ x: number; y: number }>,
  width: number,
  height: number,
): NormalizedPoint {
  return {
    x: width > 0 ? point.x / width : 0,
    y: height > 0 ? point.y / height : 0,
  };
}

export function dragPointToItemPosition(
  pointer: NormalizedPoint,
  grabOffset: NormalizedPoint,
  zoneId: RoomZoneId,
): NormalizedPoint {
  return clampToZone({
    x: pointer.x - grabOffset.x,
    y: pointer.y - grabOffset.y,
  }, zoneId);
}
