import type { RoomState } from "../model/room";

export interface RoomRenderer {
  mount(host: HTMLElement, state: RoomState): Promise<void>;
  update(state: RoomState): void;
  resize(width: number, height: number): void;
  setEditing(editing: boolean): void;
  destroy(): void;
}

export class RoomRuntime {
  private phase: "idle" | "mounting" | "mounted" = "idle";
  private disposed = false;
  private queuedState: RoomState | null = null;
  private queuedSize: Readonly<{ width: number; height: number }> | null = null;
  private queuedEditing: boolean | null = null;

  constructor(private readonly renderer: RoomRenderer) {}

  async mount(host: HTMLElement, state: RoomState): Promise<void> {
    if (this.disposed || this.phase !== "idle") return;
    this.phase = "mounting";
    try {
      await this.renderer.mount(host, state);
    } catch (error) {
      if (!this.disposed) this.phase = "idle";
      throw error;
    }
    if (this.disposed) return;
    this.phase = "mounted";
    if (this.queuedState) this.renderer.update(this.queuedState);
    if (this.queuedSize) this.renderer.resize(this.queuedSize.width, this.queuedSize.height);
    if (this.queuedEditing !== null) this.renderer.setEditing(this.queuedEditing);
    this.queuedState = null;
    this.queuedSize = null;
    this.queuedEditing = null;
  }

  update(state: RoomState): void {
    if (this.disposed) return;
    if (this.phase === "mounting") {
      this.queuedState = state;
    } else if (this.phase === "mounted") {
      this.renderer.update(state);
    }
  }

  resize(width: number, height: number): void {
    if (this.disposed || width <= 0 || height <= 0) return;
    if (this.phase === "mounting") {
      this.queuedSize = { width, height };
    } else if (this.phase === "mounted") {
      this.renderer.resize(width, height);
    }
  }

  setEditing(editing: boolean): void {
    if (this.disposed) return;
    if (this.phase === "mounting") {
      this.queuedEditing = editing;
    } else if (this.phase === "mounted") {
      this.renderer.setEditing(editing);
    }
  }

  destroy(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.queuedState = null;
    this.queuedSize = null;
    this.queuedEditing = null;
    this.renderer.destroy();
  }
}
