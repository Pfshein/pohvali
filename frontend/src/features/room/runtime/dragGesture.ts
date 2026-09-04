/**
 * Listener bookkeeping for one drag gesture. It exists as its own unit
 * because the ownership rule is easy to get wrong: only the pointer that
 * started the gesture may end it, and every listener — including the one on
 * `window` — has to come back off, whether the gesture finishes, is cancelled
 * or the whole scene is destroyed mid-drag.
 */

export interface GesturePointerEvent {
  pointerId: number;
  global: { x: number; y: number };
}

export interface GestureTarget {
  on(event: string, handler: (event: GesturePointerEvent) => void): void;
  off(event: string, handler: (event: GesturePointerEvent) => void): void;
}

export interface WindowLike {
  addEventListener(type: "blur", handler: () => void): void;
  removeEventListener(type: "blur", handler: () => void): void;
}

export interface DragGestureBinding {
  stage: GestureTarget;
  win: WindowLike;
  /** Only events carrying this pointer id may move or end the gesture. */
  pointerId: number;
  onMove: (event: GesturePointerEvent) => void;
  onCommit: () => void;
  onCancel: () => void;
}

/** Binds one gesture and returns its idempotent teardown. */
export function bindDragGesture(binding: DragGestureBinding): () => void {
  const { stage, win, pointerId, onMove, onCommit, onCancel } = binding;
  let released = false;

  const release = (): void => {
    if (released) return;
    released = true;
    stage.off("pointermove", handleMove);
    stage.off("pointerup", handleUp);
    stage.off("pointerupoutside", handleUp);
    stage.off("pointercancel", handleCancel);
    win.removeEventListener("blur", handleBlur);
  };

  function handleMove(event: GesturePointerEvent): void {
    if (event.pointerId !== pointerId) return;
    onMove(event);
  }

  // A second finger lifting must not tear down someone else's gesture.
  function handleUp(event: GesturePointerEvent): void {
    if (event.pointerId !== pointerId) return;
    release();
    onCommit();
  }

  function handleCancel(event: GesturePointerEvent): void {
    if (event.pointerId !== pointerId) return;
    release();
    onCancel();
  }

  function handleBlur(): void {
    release();
    onCancel();
  }

  stage.on("pointermove", handleMove);
  stage.on("pointerup", handleUp);
  stage.on("pointerupoutside", handleUp);
  stage.on("pointercancel", handleCancel);
  win.addEventListener("blur", handleBlur);

  return release;
}
