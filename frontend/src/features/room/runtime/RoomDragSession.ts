import { resolvePlacement } from "../model/placement";
import type { NormalizedPoint, RoomItem } from "../model/room";

export interface DragPointer {
  pointerId: number;
  /** Pointer position already normalized to the room viewport. */
  x: number;
  y: number;
}

export interface RoomDragSessionHandlers {
  /** Live (uncommitted) position while the gesture continues. */
  onPreview?: (id: string, position: NormalizedPoint) => void;
  /** Final position when the gesture ends on the pointer that started it. */
  onCommit: (id: string, position: NormalizedPoint) => void;
  /** The gesture was cancelled; the caller restores the last committed point. */
  onCancel?: (id: string) => void;
}

interface ActiveDrag {
  item: RoomItem;
  pointerId: number;
  grabOffset: NormalizedPoint;
  preview: NormalizedPoint;
}

/**
 * Owns pointer ownership rules for one room view: only the first active
 * pointer drags, previews are clamped through placement zones, a matching
 * pointerup commits, and pointercancel/blur hand the item back untouched.
 */
export class RoomDragSession {
  private active: ActiveDrag | null = null;

  constructor(private readonly handlers: RoomDragSessionHandlers) {}

  get isActive(): boolean {
    return this.active !== null;
  }

  begin(item: RoomItem, pointer: DragPointer): boolean {
    if (this.active) return false;
    this.active = {
      item,
      pointerId: pointer.pointerId,
      grabOffset: {
        x: pointer.x - item.position.x,
        y: pointer.y - item.position.y,
      },
      preview: item.position,
    };
    return true;
  }

  move(pointer: DragPointer): void {
    const active = this.active;
    if (!active || active.pointerId !== pointer.pointerId) return;
    const candidate = {
      x: pointer.x - active.grabOffset.x,
      y: pointer.y - active.grabOffset.y,
    };
    active.preview = resolvePlacement(active.item, candidate);
    this.handlers.onPreview?.(active.item.id, active.preview);
  }

  end(pointer: DragPointer): void {
    const active = this.active;
    if (!active || active.pointerId !== pointer.pointerId) return;
    this.active = null;
    this.handlers.onCommit(active.item.id, active.preview);
  }

  cancel(): void {
    const active = this.active;
    if (!active) return;
    this.active = null;
    this.handlers.onCancel?.(active.item.id);
  }
}
