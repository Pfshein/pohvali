import { describe, expect, it, vi } from "vitest";

import { bindDragGesture, type GestureTarget, type WindowLike } from "./dragGesture";

/** Minimal stand-in for the Pixi stage emitter. */
function fakeStage() {
  const handlers = new Map<string, Set<(event: unknown) => void>>();
  const target: GestureTarget = {
    on(event, handler) {
      if (!handlers.has(event)) handlers.set(event, new Set());
      handlers.get(event)!.add(handler as (event: unknown) => void);
    },
    off(event, handler) {
      handlers.get(event)?.delete(handler as (event: unknown) => void);
    },
  };
  return {
    target,
    emit(event: string, payload: unknown) {
      for (const handler of [...(handlers.get(event) ?? [])]) handler(payload);
    },
    count() {
      let total = 0;
      for (const set of handlers.values()) total += set.size;
      return total;
    },
  };
}

function fakeWindow() {
  const blurHandlers = new Set<() => void>();
  const win: WindowLike = {
    addEventListener: (_type, handler) => void blurHandlers.add(handler),
    removeEventListener: (_type, handler) => void blurHandlers.delete(handler),
  };
  return {
    win,
    blur() {
      for (const handler of [...blurHandlers]) handler();
    },
    count: () => blurHandlers.size,
  };
}

function bind(pointerId = 1) {
  const stage = fakeStage();
  const win = fakeWindow();
  const onMove = vi.fn();
  const onCommit = vi.fn();
  const onCancel = vi.fn();
  const release = bindDragGesture({
    stage: stage.target,
    win: win.win,
    pointerId,
    onMove,
    onCommit,
    onCancel,
  });
  return { stage, win, onMove, onCommit, onCancel, release };
}

const at = (pointerId: number, x = 0, y = 0) => ({ pointerId, global: { x, y } });

describe("bindDragGesture", () => {
  it("keeps the gesture alive when a different pointer is released", () => {
    const { stage, onMove, onCommit, release } = bind(1);

    stage.emit("pointerup", at(2)); // a second finger lifts elsewhere

    expect(onCommit).not.toHaveBeenCalled();

    stage.emit("pointermove", at(1, 0.4, 0.6));

    expect(onMove).toHaveBeenCalledWith(at(1, 0.4, 0.6));
    release();
  });

  it("ignores movement belonging to another pointer", () => {
    const { stage, onMove, release } = bind(1);

    stage.emit("pointermove", at(2, 0.9, 0.9));

    expect(onMove).not.toHaveBeenCalled();
    release();
  });

  it("commits and unbinds on the matching pointerup", () => {
    const { stage, win, onCommit } = bind(1);

    stage.emit("pointerup", at(1));

    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(stage.count()).toBe(0);
    expect(win.count()).toBe(0);
  });

  it("commits when the pointer is released outside the sprite", () => {
    const { stage, onCommit } = bind(3);

    stage.emit("pointerupoutside", at(3));

    expect(onCommit).toHaveBeenCalledTimes(1);
    expect(stage.count()).toBe(0);
  });

  it("cancels and unbinds on pointercancel", () => {
    const { stage, win, onCancel, onCommit } = bind(1);

    stage.emit("pointercancel", at(1));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onCommit).not.toHaveBeenCalled();
    expect(stage.count()).toBe(0);
    expect(win.count()).toBe(0);
  });

  it("cancels and unbinds when the window loses focus", () => {
    const { win, stage, onCancel } = bind(1);

    win.blur();

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(stage.count()).toBe(0);
    expect(win.count()).toBe(0);
  });

  it("releases every listener, including the window blur, on manual teardown", () => {
    const { stage, win, release, onCommit, onCancel } = bind(1);

    expect(stage.count()).toBeGreaterThan(0);
    expect(win.count()).toBe(1);

    release();

    expect(stage.count()).toBe(0);
    expect(win.count()).toBe(0);

    stage.emit("pointerup", at(1));
    expect(onCommit).not.toHaveBeenCalled();
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("is safe to release twice", () => {
    const { release, onCancel } = bind(1);

    release();

    expect(() => release()).not.toThrow();
    expect(onCancel).not.toHaveBeenCalled();
  });
});
