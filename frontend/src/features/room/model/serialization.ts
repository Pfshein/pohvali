import {
  DEFAULT_ROOM_CATALOG,
  hasRoomTemplate,
  type RoomCatalog,
} from "../catalog/roomCatalog";
import { ROOM_PLACEMENT_ZONES, type RoomZoneId } from "./placement";
import {
  ROOM_LAYER_BASE,
  ROOM_SCHEMA_VERSION,
  type RoomItem,
  type RoomLayer,
  type RoomState,
} from "./room";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isUnit(value: unknown): value is number {
  return isFiniteNumber(value) && value >= 0 && value <= 1;
}

function parseItem(value: unknown, catalog: RoomCatalog): RoomItem | null {
  if (!isRecord(value) || !isRecord(value.position)) return null;
  const { id, templateId, position, scale, rotation, layer, zIndex, zoneId, locked } = value;
  if (
    typeof id !== "string" || !id.trim()
    || typeof templateId !== "string" || !hasRoomTemplate(templateId, catalog)
    || !isUnit(position.x) || !isUnit(position.y)
    || !isFiniteNumber(scale) || scale <= 0 || scale > 4
    || !isFiniteNumber(rotation)
    || typeof layer !== "string" || !Object.hasOwn(ROOM_LAYER_BASE, layer)
    || !Number.isInteger(zIndex) || Math.abs(zIndex as number) > 999
    || typeof zoneId !== "string" || !Object.hasOwn(ROOM_PLACEMENT_ZONES, zoneId)
    || typeof locked !== "boolean"
  ) return null;
  return {
    id,
    templateId,
    position: { x: position.x, y: position.y },
    scale,
    rotation,
    layer: layer as RoomLayer,
    zIndex: zIndex as number,
    zoneId: zoneId as RoomZoneId,
    locked,
  };
}

export function serializeRoom(state: RoomState): string {
  return JSON.stringify(state);
}

export function deserializeRoom(
  json: string,
  catalog: RoomCatalog = DEFAULT_ROOM_CATALOG,
): RoomState {
  let value: unknown;
  try {
    value = JSON.parse(json);
  } catch {
    throw new Error("Invalid room state");
  }
  if (!isRecord(value) || value.schemaVersion !== ROOM_SCHEMA_VERSION || !Array.isArray(value.items)) {
    throw new Error("Invalid room state");
  }
  const items = value.items.map((item) => parseItem(item, catalog));
  if (items.some((item) => item === null)) throw new Error("Invalid room state");
  const validItems = items as RoomItem[];
  if (new Set(validItems.map((item) => item.id)).size !== validItems.length) {
    throw new Error("Invalid room state");
  }
  return { schemaVersion: ROOM_SCHEMA_VERSION, items: validItems };
}
