import {
  dragPointToItemPosition,
  type NormalizedPoint,
  type RoomZoneId,
} from "../model/placement";

interface ActiveDrag {
  readonly id: string;
  readonly pointerId: number;
  readonly origin: NormalizedPoint;
  readonly grabOffset: NormalizedPoint;
  position: NormalizedPoint;
}

export interface DragResult {
  readonly id: string;
  readonly position: NormalizedPoint;
}

export class RoomDragSession {
  private active: ActiveDrag | null = null;

  start(
    id: string,
    pointerId: number,
    itemPosition: NormalizedPoint,
    pointerPosition: NormalizedPoint,
  ): boolean {
    if (this.active) return false;
    this.active = {
      id,
      pointerId,
      origin: itemPosition,
      position: itemPosition,
      grabOffset: {
        x: pointerPosition.x - itemPosition.x,
        y: pointerPosition.y - itemPosition.y,
      },
    };
    return true;
  }

  move(pointerId: number, pointer: NormalizedPoint, zoneId: RoomZoneId): DragResult | null {
    if (!this.active || this.active.pointerId !== pointerId) return null;
    this.active.position = dragPointToItemPosition(pointer, this.active.grabOffset, zoneId);
    return { id: this.active.id, position: this.active.position };
  }

  itemId(pointerId: number): string | null {
    return this.active?.pointerId === pointerId ? this.active.id : null;
  }

  finish(pointerId: number): DragResult | null {
    if (!this.active || this.active.pointerId !== pointerId) return null;
    const result = { id: this.active.id, position: this.active.position };
    this.active = null;
    return result;
  }

  cancel(pointerId?: number): DragResult | null {
    if (!this.active || (pointerId !== undefined && this.active.pointerId !== pointerId)) return null;
    const result = { id: this.active.id, position: this.active.origin };
    this.active = null;
    return result;
  }
}
