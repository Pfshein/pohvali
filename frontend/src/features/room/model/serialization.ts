import {
  isRoomLayer,
  isRoomZoneId,
  ROOM_Z_INDEX_RANGE,
  type RoomItem,
  type RoomState,
} from "./room";

/**
 * Versioned room persistence boundary. Malformed payloads, unknown versions
 * and unknown templates are rejected before anything reaches a renderer.
 */

export type RoomParseError =
  | "malformed"
  | "unsupported-version"
  | "invalid-item"
  | "duplicate-id"
  | "unknown-template";

export interface RoomTemplateLookup {
  has(templateId: string): boolean;
}

export type ParseRoomResult =
  | { ok: true; state: RoomState }
  | { ok: false; error: RoomParseError };

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isNormalizedPoint(value: unknown): value is { x: number; y: number } {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  if (!isFiniteNumber(record.x) || !isFiniteNumber(record.y)) return false;
  return record.x >= 0 && record.x <= 1 && record.y >= 0 && record.y <= 1;
}

function isRoomItem(value: unknown): boolean {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string"
    && record.id.length > 0
    && typeof record.templateId === "string"
    && record.templateId.length > 0
    && isNormalizedPoint(record.position)
    && isFiniteNumber(record.scale)
    && record.scale > 0
    && isFiniteNumber(record.rotation)
    && isRoomLayer(record.layer)
    && typeof record.zIndex === "number"
    && Number.isInteger(record.zIndex)
    && record.zIndex >= ROOM_Z_INDEX_RANGE.min
    && record.zIndex <= ROOM_Z_INDEX_RANGE.max
    && isRoomZoneId(record.zoneId)
    && typeof record.locked === "boolean"
  );
}

export function parseRoomState(raw: string, templates: RoomTemplateLookup): ParseRoomResult {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return { ok: false, error: "malformed" };
  }

  if (typeof value !== "object" || value === null || !Array.isArray((value as { items?: unknown }).items)) {
    return { ok: false, error: "malformed" };
  }
  const record = value as { schemaVersion?: unknown; items: unknown[] };
  if (record.schemaVersion !== 1) return { ok: false, error: "unsupported-version" };
  if (!record.items.every(isRoomItem)) return { ok: false, error: "invalid-item" };

  const seen = new Set<string>();
  for (const item of record.items as RoomItem[]) {
    if (seen.has(item.id)) return { ok: false, error: "duplicate-id" };
    seen.add(item.id);
  }
  for (const item of record.items as RoomItem[]) {
    if (!templates.has(item.templateId)) return { ok: false, error: "unknown-template" };
  }

  return { ok: true, state: { schemaVersion: 1, items: record.items as RoomItem[] } };
}

export function serializeRoomState(state: RoomState): string {
  return JSON.stringify({ schemaVersion: 1, items: state.items });
}
