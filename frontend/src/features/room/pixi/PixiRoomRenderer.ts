import { Application, Assets, Container, FillGradient, Graphics, Sprite, Texture } from "pixi.js";

import type { RoomCatalog } from "../catalog/roomCatalog";
import { isMovableItem } from "../model/placement";
import type { NormalizedPoint, RoomItem, RoomItemMoveHandler, RoomState } from "../model/room";
import { RoomDragSession, type DragPointer } from "../runtime/RoomDragSession";
import {
  bindDragGesture,
  type GesturePointerEvent,
  type GestureTarget,
} from "../runtime/dragGesture";
import type { RoomRenderer } from "../runtime/RoomRuntime";
import { planScene, type SceneSprite } from "./scenePlan";

/**
 * Wall and floor colours mirror the --room-wall / --room-floor tokens; the
 * floor line matches ROOM_FLOOR_LINE so placement zones and paint agree.
 */
const WALL_TOP = 0xf9ddb4;
const WALL_BOTTOM = 0xf2c997;
const FLOOR_TOP = 0xe8bd82;
const FLOOR_BOTTOM = 0xdfb071;
const FLOOR_LINE_COLOR = 0xc99e63;
const PLACEHOLDER_FILL = 0xd9c9a8;
const EDITING_OUTLINE = 0x74754b;

export interface PixiRoomRendererOptions {
  catalog: RoomCatalog;
  onItemMove: RoomItemMoveHandler;
}

interface SpriteEntry {
  sprite: Sprite | Graphics;
  textureUrl: string | null;
}

/**
 * The visual half of the room (spec section 5): Pixi owns the canvas,
 * textures, layering and pointer lifecycle only. It never calls APIs,
 * opens dialogs or stores product data; its single outgoing signal is the
 * confirmed item move passed to onItemMove.
 */
export class PixiRoomRenderer implements RoomRenderer {
  private app: Application | null = null;
  private background: Graphics | null = null;
  private itemLayer: Container | null = null;
  private editingLayer: Graphics | null = null;
  private entries = new Map<string, SpriteEntry>();
  private items = new Map<string, RoomItem>();
  private state: RoomState | null = null;
  private view = { width: 0, height: 0 };
  private editing = false;
  private destroyed = false;
  private planVersion = 0;
  /** Teardown of the gesture in flight, so destroy() never strands listeners. */
  private releaseGesture: (() => void) | null = null;
  private readonly drag: RoomDragSession;

  constructor(private readonly options: PixiRoomRendererOptions) {
    this.drag = new RoomDragSession({
      onPreview: (id, position) => this.previewMove(id, position),
      onCommit: (id, position) => this.options.onItemMove(id, position),
      onCancel: (id) => this.syncItem(id),
    });
  }

  async mount(host: HTMLElement, state: RoomState): Promise<void> {
    const app = new Application();
    try {
      await app.init({
        backgroundAlpha: 0,
        antialias: true,
        resolution: Math.min(window.devicePixelRatio || 1, 2),
        autoDensity: true,
        // Keeps canvas.toDataURL() meaningful for QA pixel checks.
        preserveDrawingBuffer: true,
        width: host.clientWidth || 1,
        height: host.clientHeight || 1,
      });
    } catch (error) {
      // No GPU context: release the half-built application rather than
      // stranding it, then let RoomRuntime absorb the failure. The DOM room
      // above the canvas stays fully usable.
      this.destroyed = true;
      try {
        app.destroy();
      } catch {
        /* a renderer that never initialised may refuse to tear down */
      }
      throw error;
    }
    if (this.destroyed) {
      // destroy() ran while the async init was in flight (StrictMode).
      app.destroy();
      return;
    }
    app.canvas.style.width = "100%";
    app.canvas.style.height = "100%";
    app.canvas.style.display = "block";
    host.appendChild(app.canvas);
    this.app = app;

    this.background = new Graphics();
    this.itemLayer = new Container();
    this.itemLayer.sortableChildren = true;
    this.editingLayer = new Graphics();
    app.stage.addChild(this.background, this.itemLayer, this.editingLayer);
    app.stage.eventMode = "static";
    app.stage.hitArea = app.screen;

    this.view = { width: app.renderer.width, height: app.renderer.height };
    this.paintBackground();
    this.update(state);
  }

  update(state: RoomState): void {
    this.state = state;
    if (!this.app || !this.itemLayer) return;

    this.items = new Map(state.items.map((item) => [item.id, item]));
    const plan = planScene(state, this.options.catalog, this.view);
    const version = this.planVersion + 1;
    this.planVersion = version;

    const seen = new Set<string>();
    let order = 0;
    for (const spritePlan of plan.sprites) {
      seen.add(spritePlan.id);
      void this.syncSprite(spritePlan, order, version);
      order += 1;
    }
    for (const [id, entry] of this.entries) {
      if (!seen.has(id)) {
        entry.sprite.destroy();
        this.entries.delete(id);
      }
    }
    this.drawEditingOutlines();
  }

  resize(width: number, height: number): void {
    if (!this.app) return;
    this.view = { width, height };
    this.app.renderer.resize(width, height);
    if (this.app.stage.hitArea) {
      this.app.stage.hitArea = this.app.screen;
    }
    this.paintBackground();
    if (this.state) this.update(this.state);
  }

  setEditing(editing: boolean): void {
    this.editing = editing;
    this.drawEditingOutlines();
  }

  destroy(): void {
    this.destroyed = true;
    // A gesture may still be in flight; its window listener outlives the
    // stage, so it has to come off explicitly.
    this.releaseGesture?.();
    this.releaseGesture = null;
    this.drag.cancel();
    if (!this.app) return;
    this.app.destroy(true, { children: true });
    this.app = null;
    this.background = null;
    this.itemLayer = null;
    this.editingLayer = null;
    this.entries.clear();
    this.items.clear();
    this.state = null;
  }

  private paintBackground(): void {
    const graphics = this.background;
    if (!graphics) return;
    const { width, height } = this.view;
    const floorY = height * 0.56;

    graphics.clear();

    const wall = new FillGradient(0, 0, 0, floorY);
    wall.addColorStop(0, WALL_TOP);
    wall.addColorStop(1, WALL_BOTTOM);
    graphics.rect(0, 0, width, floorY).fill(wall);

    const floor = new FillGradient(0, floorY, 0, height);
    floor.addColorStop(0, FLOOR_TOP);
    floor.addColorStop(1, FLOOR_BOTTOM);
    graphics.rect(0, floorY, width, height - floorY).fill(floor);

    graphics.rect(0, floorY - 1.5, width, 3).fill({ color: FLOOR_LINE_COLOR, alpha: 0.5 });

    // Soft warm light pooling behind the seat.
    graphics
      .ellipse(width / 2, floorY - height * 0.05, width * 0.42, height * 0.16)
      .fill({ color: 0xfff3dc, alpha: 0.22 });
  }

  private async syncSprite(plan: SceneSprite, order: number, version: number): Promise<void> {
    const layer = this.itemLayer;
    if (!layer) return;

    if (plan.placeholder || !plan.src) {
      this.ensureEntry(plan, order, null);
      return;
    }

    let texture: Texture | null;
    try {
      texture = await Assets.load(plan.src);
    } catch {
      texture = null; // calm neutral placeholder; the DOM UI keeps working
    }
    if (this.destroyed || version !== this.planVersion || !this.app) return;
    this.ensureEntry(plan, order, texture);
  }

  private ensureEntry(plan: SceneSprite, order: number, texture: Texture | null): void {
    const layer = this.itemLayer;
    if (!layer) return;
    const item = this.items.get(plan.id);
    let entry = this.entries.get(plan.id);

    if (entry && entry.textureUrl !== (texture ? plan.src : null)) {
      entry.sprite.destroy();
      this.entries.delete(plan.id);
      entry = undefined;
    }

    if (!entry) {
      const sprite = texture ? new Sprite(texture) : new Graphics();
      sprite.eventMode = "static";
      layer.addChild(sprite);
      entry = { sprite, textureUrl: texture ? plan.src : null };
      this.entries.set(plan.id, entry);
      this.wirePointerEvents(entry.sprite, plan.id);
    }

    const sprite = entry.sprite;
    if (sprite instanceof Sprite) {
      sprite.anchor.set(plan.anchor.x, plan.anchor.y);
      // contain-fit inside the planned square, like object-fit: contain
      const ratio = texture ? texture.width / texture.height : 1;
      const width = ratio >= 1 ? plan.width : plan.width * ratio;
      const height = ratio >= 1 ? plan.width / ratio : plan.height;
      sprite.width = width;
      sprite.height = height;
    } else {
      this.resizePlaceholder(sprite, plan);
    }
    sprite.position.set(plan.x, plan.y);
    sprite.zIndex = order;
    sprite.cursor = item && isMovableItem(item) ? "grab" : "default";
  }

  private resizePlaceholder(graphics: Graphics, plan: SceneSprite): void {
    graphics.clear();
    graphics
      .roundRect(
        -plan.width * plan.anchor.x,
        -plan.height * plan.anchor.y,
        plan.width,
        plan.height,
        Math.min(plan.width, plan.height) * 0.12,
      )
      .fill({ color: PLACEHOLDER_FILL, alpha: 0.92 });
  }

  private wirePointerEvents(sprite: Sprite | Graphics, id: string): void {
    sprite.on("pointerdown", (event: GesturePointerEvent) => {
      const item = this.items.get(id);
      if (!item || !isMovableItem(item) || !this.app) return;
      const pointer = this.toNormalized(event.pointerId, event.global.x, event.global.y);
      if (!this.drag.begin(item, pointer)) return;

      const { pointerId } = event;
      this.releaseGesture = bindDragGesture({
        stage: this.app.stage as unknown as GestureTarget,
        win: window,
        pointerId,
        onMove: (moveEvent) => {
          this.drag.move(
            this.toNormalized(moveEvent.pointerId, moveEvent.global.x, moveEvent.global.y),
          );
        },
        onCommit: () => {
          this.releaseGesture = null;
          this.drag.end({ pointerId, x: 0, y: 0 });
        },
        onCancel: () => {
          this.releaseGesture = null;
          this.drag.cancel();
        },
      });
    });
  }

  private toNormalized(pointerId: number, x: number, y: number): DragPointer {
    return {
      pointerId,
      x: this.view.width > 0 ? x / this.view.width : 0,
      y: this.view.height > 0 ? y / this.view.height : 0,
    };
  }

  private previewMove(id: string, position: NormalizedPoint): void {
    const entry = this.entries.get(id);
    if (!entry) return;
    entry.sprite.position.set(position.x * this.view.width, position.y * this.view.height);
  }

  private syncItem(id: string): void {
    const item = this.items.get(id);
    if (!item) return;
    const entry = this.entries.get(id);
    if (entry) {
      entry.sprite.position.set(
        item.position.x * this.view.width,
        item.position.y * this.view.height,
      );
    }
  }

  private drawEditingOutlines(): void {
    const graphics = this.editingLayer;
    if (!graphics) return;
    graphics.clear();
    if (!this.editing || !this.state) return;

    for (const item of this.state.items) {
      if (!isMovableItem(item)) continue;
      const entry = this.entries.get(item.id);
      if (!entry) continue;
      const sprite = entry.sprite;
      const anchorY = sprite instanceof Sprite ? sprite.anchor.y : 0.5;
      const top = sprite.y - sprite.height * anchorY;
      graphics
        .roundRect(sprite.x - sprite.width / 2 - 6, top - 6, sprite.width + 12, sprite.height + 12, 14)
        .stroke({ width: 2, color: EDITING_OUTLINE, alpha: 0.55 });
    }
  }
}
