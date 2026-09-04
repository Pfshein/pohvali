import {
  Application,
  Assets,
  Container,
  type FederatedPointerEvent,
  Graphics,
  Rectangle,
  Sprite,
  type Texture,
} from "pixi.js";

import { getRoomTemplate, type RoomCatalog } from "../catalog/roomCatalog";
import { screenToNormalized, type NormalizedPoint } from "../model/placement";
import { compareRoomItems, type RoomItem, type RoomState } from "../model/room";
import { RoomDragSession } from "../runtime/RoomDragSession";
import type { RoomRenderer } from "../runtime/RoomRuntime";
import { ViewGeneration } from "../runtime/ViewGeneration";

type ViewKind = "chair" | "texture" | "placeholder";

interface ItemView {
  readonly container: Container;
  readonly kind: ViewKind;
  item: RoomItem;
}

export type RoomItemMoveHandler = (id: string, position: NormalizedPoint) => void;

export class PixiRoomRenderer implements RoomRenderer {
  private readonly app = new Application();
  private readonly background = new Graphics();
  private readonly world = new Container();
  private readonly views = new Map<string, ItemView>();
  private readonly generations = new ViewGeneration();
  private readonly sortOrder = new Map<string, number>();
  private state: RoomState = { schemaVersion: 1, items: [] };
  private width = 1;
  private height = 1;
  private editing = false;
  private destroyed = false;
  private readonly drag = new RoomDragSession();

  constructor(
    private readonly catalog: RoomCatalog,
    private readonly onItemMove: RoomItemMoveHandler,
  ) {}

  async mount(host: HTMLElement, state: RoomState): Promise<void> {
    const bounds = host.getBoundingClientRect();
    this.width = Math.max(1, Math.round(bounds.width));
    this.height = Math.max(1, Math.round(bounds.height));
    await this.app.init({
      width: this.width,
      height: this.height,
      backgroundAlpha: 0,
      antialias: true,
      autoDensity: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
    });
    if (this.destroyed) {
      this.app.destroy({ removeView: true }, { children: true });
      return;
    }
    this.world.sortableChildren = true;
    this.app.stage.addChild(this.background, this.world);
    this.app.stage.eventMode = "static";
    this.app.stage.on("globalpointermove", this.handlePointerMove);
    this.app.stage.on("pointerup", this.finishDrag);
    this.app.stage.on("pointerupoutside", this.finishDrag);
    this.app.canvas.addEventListener("pointercancel", this.handleNativePointerCancel);
    window.addEventListener("blur", this.handleWindowBlur);
    host.appendChild(this.app.canvas);
    this.resize(this.width, this.height);
    this.update(state);
  }

  update(state: RoomState): void {
    if (this.destroyed) return;
    this.state = state;
    const nextIds = new Set(state.items.map((item) => item.id));
    this.generations.cancelMissing(nextIds);
    this.sortOrder.clear();
    [...state.items].sort(compareRoomItems).forEach((item, index) => {
      this.sortOrder.set(item.id, index);
    });
    for (const [id, view] of this.views) {
      const next = state.items.find((item) => item.id === id);
      if (!next || next.templateId !== view.item.templateId) {
        view.container.destroy({ children: true });
        this.views.delete(id);
      }
    }
    for (const item of state.items) {
      const view = this.views.get(item.id);
      if (view) {
        view.item = item;
        this.applyViewState(view);
      } else if (!this.generations.isPending(item.id, item.templateId)) {
        this.requestView(item);
      }
    }
  }

  resize(width: number, height: number): void {
    if (this.destroyed || width <= 0 || height <= 0) return;
    this.width = Math.max(1, Math.round(width));
    this.height = Math.max(1, Math.round(height));
    this.app.renderer.resize(this.width, this.height);
    this.app.stage.hitArea = new Rectangle(0, 0, this.width, this.height);
    this.drawRoom();
    for (const view of this.views.values()) this.applyViewState(view);
  }

  setEditing(editing: boolean): void {
    this.editing = editing;
    if (!editing) this.restoreCancelledDrag();
    for (const view of this.views.values()) this.applyInteraction(view);
  }

  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.restoreCancelledDrag();
    this.app.stage.off("globalpointermove", this.handlePointerMove);
    this.app.stage.off("pointerup", this.finishDrag);
    this.app.stage.off("pointerupoutside", this.finishDrag);
    if (this.app.renderer) {
      this.app.canvas.removeEventListener("pointercancel", this.handleNativePointerCancel);
      window.removeEventListener("blur", this.handleWindowBlur);
      this.app.destroy({ removeView: true }, { children: true });
    }
    this.views.clear();
    this.generations.clear();
  }

  private async createView(item: RoomItem): Promise<ItemView> {
    const template = getRoomTemplate(item.templateId, this.catalog);
    const asset = this.catalog.assets[template.assetId];
    if (!asset) return this.createPlaceholder(item);
    if (asset.kind === "procedural") return this.createChair(item);
    try {
      const texture = await Assets.load<Texture>(asset.src);
      const container = new Container();
      const sprite = new Sprite(texture);
      sprite.anchor.set(0.5, 1);
      container.addChild(sprite);
      return { container, kind: "texture", item };
    } catch {
      return this.createPlaceholder(item);
    }
  }

  private createChair(item: RoomItem): ItemView {
    const container = new Container();
    const chair = new Graphics()
      .roundRect(-55, -110, 110, 90, 28).fill({ color: 0xd7c6ee })
      .roundRect(-64, -63, 128, 72, 25).fill({ color: 0xc7b1e4 })
      .roundRect(-52, -52, 104, 48, 18).fill({ color: 0xe4d9f2 })
      .rect(-48, 5, 12, 24).fill({ color: 0x816b5d })
      .rect(36, 5, 12, 24).fill({ color: 0x816b5d });
    container.addChild(chair);
    return { container, kind: "chair", item };
  }

  private createPlaceholder(item: RoomItem): ItemView {
    const container = new Container();
    container.addChild(new Graphics().circle(0, -45, 36).fill({ color: 0xcfe6d0 }));
    return { container, kind: "placeholder", item };
  }

  private bindPointerEvents(view: ItemView): void {
    view.container.on("pointerdown", (event: FederatedPointerEvent) => {
      if (!this.editing || view.item.locked) return;
      event.stopPropagation();
      const pointer = screenToNormalized(event.global, this.width, this.height);
      this.drag.start(view.item.id, event.pointerId, view.item.position, pointer);
    });
  }

  private applyInteraction(view: ItemView): void {
    const interactive = this.editing && !view.item.locked;
    view.container.eventMode = interactive ? "static" : "none";
    view.container.cursor = interactive ? "grab" : "default";
  }

  private applyViewState(view: ItemView): void {
    const { item, container } = view;
    container.position.set(item.position.x * this.width, item.position.y * this.height);
    container.rotation = item.rotation;
    container.zIndex = this.sortOrder.get(item.id) ?? 0;
    const viewportScale = Math.min(this.width / 390, this.height / 700);
    if (view.kind === "texture") {
      const sprite = container.children[0] as Sprite;
      const targetHeight = this.height * 0.3 * item.scale;
      const ratio = sprite.texture.height > 0 ? sprite.texture.width / sprite.texture.height : 0.7;
      sprite.height = targetHeight;
      sprite.width = targetHeight * ratio;
      container.scale.set(1);
    } else {
      container.scale.set(viewportScale * item.scale);
    }
    this.applyInteraction(view);
  }

  private readonly handlePointerMove = (event: FederatedPointerEvent): void => {
    const id = this.drag.itemId(event.pointerId);
    if (!id) return;
    const view = this.views.get(id);
    if (!view) return;
    const pointer = screenToNormalized(event.global, this.width, this.height);
    const moved = this.drag.move(event.pointerId, pointer, view.item.zoneId);
    if (!moved) return;
    const movedView = this.views.get(moved.id);
    movedView?.container.position.set(moved.position.x * this.width, moved.position.y * this.height);
  };

  private readonly finishDrag = (event: FederatedPointerEvent): void => {
    const result = this.drag.finish(event.pointerId);
    if (result) this.onItemMove(result.id, result.position);
  };

  private readonly handleNativePointerCancel = (event: PointerEvent): void => {
    this.restoreCancelledDrag(event.pointerId);
  };

  private readonly handleWindowBlur = (): void => {
    this.restoreCancelledDrag();
  };

  private restoreCancelledDrag(pointerId?: number): void {
    const cancelled = this.drag.cancel(pointerId);
    if (!cancelled) return;
    const view = this.views.get(cancelled.id);
    view?.container.position.set(
      cancelled.position.x * this.width,
      cancelled.position.y * this.height,
    );
  }

  private requestView(item: RoomItem): void {
    const token = this.generations.begin(item.id, item.templateId);
    void this.createView(item).then((created) => {
      if (!this.generations.complete(item.id, token)) {
        created.container.destroy({ children: true });
        return;
      }
      const current = this.state.items.find((candidate) => candidate.id === item.id);
      if (this.destroyed || !current || current.templateId !== item.templateId) {
        created.container.destroy({ children: true });
        if (current && !this.destroyed) this.requestView(current);
        return;
      }
      created.item = current;
      this.views.set(item.id, created);
      this.world.addChild(created.container);
      this.bindPointerEvents(created);
      this.applyViewState(created);
    });
  }

  private drawRoom(): void {
    const wallHeight = this.height * 0.62;
    this.background.clear()
      .rect(0, 0, this.width, wallHeight).fill({ color: 0xf7eddf })
      .rect(0, wallHeight, this.width, this.height - wallHeight).fill({ color: 0xdcccb8 })
      .rect(0, wallHeight - 3, this.width, 6).fill({ color: 0xcbb8a0 });
  }
}
