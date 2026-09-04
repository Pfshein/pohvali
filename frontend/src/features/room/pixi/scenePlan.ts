import { sortRoomItems, type RoomItem, type RoomState } from "../model/room";
import type { RoomCatalog, RoomItemTemplate } from "../catalog/roomCatalog";

/**
 * Pure geometry between RoomState and Pixi: normalized state is turned into
 * pixel sprites for the current viewport only. Nothing here mutates state, so
 * resizing is always a re-plan, never a data change.
 */

export interface SceneView {
  width: number;
  height: number;
}

export interface SceneSprite {
  id: string;
  zIndex: number;
  /** Anchor point of the texture in 0…1 texture space (Pixi anchor). */
  anchor: { x: number; y: number };
  /** Sprite anchor position in pixels. */
  x: number;
  y: number;
  width: number;
  height: number;
  src: string | null;
  /** True when the texture cannot be resolved; the renderer draws a calm neutral shape. */
  placeholder: boolean;
}

export interface ScenePlan {
  sprites: readonly SceneSprite[];
}

/** Fraction of the viewport the chair occupies (mockup: ~0.9 screen width). */
const CHAIR_SIZE_RATIO = 0.92;
const CHAIR_MAX_HEIGHT_RATIO = 0.5;
const MASCOT_SIZE_RATIO = 0.55;

/**
 * Anchors inside each texture, tuned against the approved mockup and the
 * chair art in scripts/room-assets/.
 *
 * The chair is anchored at its floor contact. The mascot is NOT: sharing that
 * point drops the character to the chair's feet, where the front cushion
 * buries everything but its head. CHAIR_SEAT_POINT is where the cushion
 * surface sits inside the chair texture, and the mascot's own base
 * (MASCOT_ANCHOR) is lifted onto it.
 */
const CHAIR_ANCHOR = { x: 0.5, y: 0.91 } as const;
const CHAIR_SEAT_POINT = { x: 0.5, y: 0.67 } as const;
const MASCOT_ANCHOR = { x: 0.5, y: 0.88 } as const;

function isMascotTemplate(template: RoomItemTemplate | undefined): boolean {
  return template?.templateId.startsWith("mascot.") ?? false;
}

function chairSize(view: SceneView): number {
  return Math.min(CHAIR_SIZE_RATIO * view.width, CHAIR_MAX_HEIGHT_RATIO * view.height);
}

function textureSize(template: RoomItemTemplate | undefined, view: SceneView): number {
  const chair = chairSize(view);
  return isMascotTemplate(template) ? chair * MASCOT_SIZE_RATIO : chair;
}

function anchorFor(template: RoomItemTemplate | undefined): { x: number; y: number } {
  return isMascotTemplate(template) ? MASCOT_ANCHOR : CHAIR_ANCHOR;
}

/** Lift from the shared room point up to the seat, in pixels. */
function seatOffsetY(template: RoomItemTemplate | undefined, view: SceneView): number {
  if (!isMascotTemplate(template)) return 0;
  return (CHAIR_SEAT_POINT.y - CHAIR_ANCHOR.y) * chairSize(view);
}

export function planScene(state: RoomState, catalog: RoomCatalog, view: SceneView): ScenePlan {
  const sprites = sortRoomItems([...state.items]).map((item: RoomItem): SceneSprite => {
    const template = catalog.templates.get(item.templateId);
    const textureAsset = template?.assets.find((asset) => asset.kind === "texture");
    const size = textureSize(template, view) * item.scale;
    return {
      id: item.id,
      zIndex: item.zIndex,
      anchor: anchorFor(template),
      x: item.position.x * view.width,
      y: item.position.y * view.height + seatOffsetY(template, view),
      width: size,
      height: size,
      src: textureAsset && textureAsset.kind === "texture" ? textureAsset.src : null,
      placeholder: !textureAsset,
    };
  });
  return { sprites };
}
