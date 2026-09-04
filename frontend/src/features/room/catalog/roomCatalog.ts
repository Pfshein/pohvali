import type { NormalizedPoint, RoomZoneId } from "../model/placement";
import type { RoomItem, RoomLayer } from "../model/room";

export type RoomAsset =
  | Readonly<{ kind: "texture"; src: string }>
  | Readonly<{ kind: "procedural"; renderer: "chair" }>;

export interface RoomItemTemplate {
  readonly id: string;
  readonly assetId: string;
  readonly label: string;
  readonly defaultPosition: NormalizedPoint;
  readonly defaultScale: number;
  readonly defaultRotation: number;
  readonly layer: RoomLayer;
  readonly zIndex: number;
  readonly zoneId: RoomZoneId;
  readonly locked: boolean;
}

export interface RoomMascotAsset {
  readonly code: string;
  readonly label: string;
  readonly assetPath: string;
}

export interface RoomCatalog {
  readonly assets: Readonly<Record<string, RoomAsset>>;
  readonly templates: Readonly<Record<string, RoomItemTemplate>>;
}

const DEFAULT_MASCOTS: readonly RoomMascotAsset[] = [
  { code: "ava", label: "Авокадо Ава", assetPath: "/assets/mascots/ava.png" },
  { code: "pol", label: "Пингвин Поль", assetPath: "/assets/mascots/pol.png" },
  { code: "mira", label: "Кошка Мира", assetPath: "/assets/mascots/mira.png" },
  { code: "tisha", label: "Капибара Тиша", assetPath: "/assets/mascots/tisha.png" },
  { code: "lumi", label: "Облачко Луми", assetPath: "/assets/mascots/lumi.png" },
  { code: "bim", label: "Лягушонок Бим", assetPath: "/assets/mascots/bim.png" },
];

export function createRoomCatalog(mascots: readonly RoomMascotAsset[] = DEFAULT_MASCOTS): RoomCatalog {
  const chair = {
    id: "chair.basic",
    assetId: "chair.basic",
    label: "Базовое кресло",
    defaultPosition: { x: 0.62, y: 0.78 },
    defaultScale: 1,
    defaultRotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId: "floor",
    locked: false,
  } satisfies RoomItemTemplate;
  const mascotTemplates = mascots.map((mascot) => ({
    id: `mascot.${mascot.code}`,
    assetId: `mascot.${mascot.code}`,
    label: mascot.label,
    defaultPosition: { x: 0.43, y: 0.8 },
    defaultScale: 1,
    defaultRotation: 0,
    layer: "mascot",
    zIndex: 0,
    zoneId: "floor",
    locked: false,
  } satisfies RoomItemTemplate));
  return {
    assets: {
      "chair.basic": { kind: "procedural", renderer: "chair" },
      ...Object.fromEntries(mascots.map((mascot) => [
        `mascot.${mascot.code}`,
        { kind: "texture", src: mascot.assetPath } satisfies RoomAsset,
      ])),
    },
    templates: {
      "chair.basic": chair,
      ...Object.fromEntries(mascotTemplates.map((template) => [template.id, template])),
    },
  };
}

export const DEFAULT_ROOM_CATALOG = createRoomCatalog();
export const ROOM_ASSETS = DEFAULT_ROOM_CATALOG.assets;
export const ROOM_ITEM_TEMPLATES = DEFAULT_ROOM_CATALOG.templates;

type RoomItemOverrides = Partial<Pick<
  RoomItem,
  "position" | "scale" | "rotation" | "layer" | "zIndex" | "zoneId" | "locked"
>>;

export function hasRoomTemplate(
  templateId: string,
  catalog: RoomCatalog = DEFAULT_ROOM_CATALOG,
): boolean {
  return Object.hasOwn(catalog.templates, templateId);
}

export function getRoomTemplate(
  templateId: string,
  catalog: RoomCatalog = DEFAULT_ROOM_CATALOG,
): RoomItemTemplate {
  const template = catalog.templates[templateId];
  if (!template) throw new Error(`Unknown room item template: ${templateId}`);
  return template;
}

export function instantiateRoomItem(
  templateId: string,
  instanceId: string,
  overrides: RoomItemOverrides = {},
  catalog: RoomCatalog = DEFAULT_ROOM_CATALOG,
): RoomItem {
  if (!instanceId.trim()) throw new Error("Room item instance id must not be empty");
  const template = getRoomTemplate(templateId, catalog);
  return {
    id: instanceId,
    templateId,
    position: overrides.position ?? { ...template.defaultPosition },
    scale: overrides.scale ?? template.defaultScale,
    rotation: overrides.rotation ?? template.defaultRotation,
    layer: overrides.layer ?? template.layer,
    zIndex: overrides.zIndex ?? template.zIndex,
    zoneId: overrides.zoneId ?? template.zoneId,
    locked: overrides.locked ?? template.locked,
  };
}
