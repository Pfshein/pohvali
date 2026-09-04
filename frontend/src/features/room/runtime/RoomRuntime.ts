import type { RoomState } from "../model/room";

/**
 * Fixed lifecycle contract between React and the room renderer (spec
 * section 5). Pixi implements it; React only ever talks to this interface.
 */
export interface RoomRenderer {
  mount(host: HTMLElement, state: RoomState): Promise<void>;
  update(state: RoomState): void;
  resize(width: number, height: number): void;
  setEditing(editing: boolean): void;
  destroy(): void;
}

type QueuedOperation =
  | { kind: "update"; state: RoomState }
  | { kind: "resize"; width: number; height: number }
  | { kind: "editing"; editing: boolean };

/**
 * Bridges React's synchronous renders with an async renderer mount. Calls
 * that arrive before the mount settles are queued and replayed in order; a
 * destroy during mounting tears the renderer down the moment it appears and
 * drops everything queued (the StrictMode mount → cleanup → mount case).
 */
export class RoomRuntime {
  private mounting = false;
  private destroyed = false;
  private rendererDestroyed = false;
  private queue: QueuedOperation[] = [];

  constructor(private readonly renderer: RoomRenderer) {}

  async mount(host: HTMLElement, state: RoomState): Promise<void> {
    if (this.destroyed) return;
    this.mounting = true;
    let failed = false;
    try {
      await this.renderer.mount(host, state);
    } catch {
      // A renderer that cannot start (no WebGL, lost context) must not reject
      // into the caller's `void mount(...)`. It is torn down and the runtime
      // goes inert; the DOM room above the canvas keeps working.
      failed = true;
    } finally {
      this.mounting = false;
    }
    if (failed || this.destroyed) {
      this.destroyed = true;
      this.queue = [];
      this.teardownRenderer();
      return;
    }
    const queued = this.queue;
    this.queue = [];
    for (const operation of queued) this.apply(operation);
  }

  update(state: RoomState): void {
    this.enqueue({ kind: "update", state });
  }

  resize(width: number, height: number): void {
    this.enqueue({ kind: "resize", width, height });
  }

  setEditing(editing: boolean): void {
    this.enqueue({ kind: "editing", editing });
  }

  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.queue = [];
    if (!this.mounting) this.teardownRenderer();
  }

  /** The renderer is released exactly once, whether it mounted or failed. */
  private teardownRenderer(): void {
    if (this.rendererDestroyed) return;
    this.rendererDestroyed = true;
    this.renderer.destroy();
  }

  private enqueue(operation: QueuedOperation): void {
    if (this.destroyed) return;
    if (this.mounting) {
      this.queue.push(operation);
      return;
    }
    this.apply(operation);
  }

  private apply(operation: QueuedOperation): void {
    switch (operation.kind) {
      case "update":
        this.renderer.update(operation.state);
        break;
      case "resize":
        this.renderer.resize(operation.width, operation.height);
        break;
      case "editing":
        this.renderer.setEditing(operation.editing);
        break;
    }
  }
}
