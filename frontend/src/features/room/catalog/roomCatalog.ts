import type { NormalizedPoint, RoomItem, RoomLayer, RoomZoneId } from "../model/room";

/**
 * Room asset manifest (spec section 11). The chair layers are original
 * in-repo vector art (see frontend/scripts/room-assets/) rasterized to
 * transparent WebP — no third-party artwork or license is involved.
 */
export type RoomAsset =
  | { kind: "texture"; src: string }
  | { kind: "procedural"; renderer: "room-background" };

/** The minimum the room needs to seat whichever mascot the server returned. */
export interface RoomMascotAsset {
  code: string;
  name: string;
  assetPath: string;
}

export interface RoomItemTemplate {
  templateId: string;
  layer: RoomLayer;
  zIndex: number;
  zoneId: RoomZoneId;
  scale: number;
  locked: boolean;
  assets: readonly RoomAsset[];
}

export interface RoomCatalog {
  readonly templates: ReadonlyMap<string, RoomItemTemplate>;
  has(templateId: string): boolean;
}

interface RoomItemInit {
  id: string;
  position: NormalizedPoint;
  scale?: number;
  rotation?: number;
  zIndex?: number;
  locked?: boolean;
}

function chairTemplate(
  templateId: string,
  layer: RoomLayer,
  src: string,
): RoomItemTemplate {
  return {
    templateId,
    layer,
    zIndex: 0,
    zoneId: "fixed",
    scale: 1,
    locked: true,
    assets: [{ kind: "texture", src }],
  };
}

/**
 * Templates and assets live here; the UI creates only instances. Mascot
 * templates are generated from the supplied collection response, so mascots
 * added through admin work without a frontend change.
 */
export function createRoomCatalog(mascots: readonly RoomMascotAsset[]): RoomCatalog {
  const templates = new Map<string, RoomItemTemplate>();

  templates.set("chair.basic.back", chairTemplate(
    "chair.basic.back",
    "furniture",
    "/assets/room/v2/chair-back.webp",
  ));
  templates.set("chair.basic.front", chairTemplate(
    "chair.basic.front",
    "foreground",
    "/assets/room/v2/chair-front.webp",
  ));

  for (const mascot of mascots) {
    templates.set(`mascot.${mascot.code}`, {
      templateId: `mascot.${mascot.code}`,
      layer: "mascot",
      zIndex: 0,
      zoneId: "fixed",
      scale: 1,
      locked: true,
      assets: [{ kind: "texture", src: mascot.assetPath }],
    });
  }

  return {
    templates,
    has: (templateId) => templates.has(templateId),
  };
}

/** All room elements are created through this factory, never inside a renderer. */
export function instantiateRoomItem(
  catalog: RoomCatalog,
  templateId: string,
  init: RoomItemInit,
): RoomItem {
  const template = catalog.templates.get(templateId);
  if (!template) throw new Error(`Unknown room template: ${templateId}`);
  return {
    id: init.id,
    templateId,
    position: init.position,
    scale: init.scale ?? template.scale,
    rotation: init.rotation ?? 0,
    layer: template.layer,
    zIndex: init.zIndex ?? template.zIndex,
    zoneId: template.zoneId,
    locked: init.locked ?? template.locked,
  };
}
