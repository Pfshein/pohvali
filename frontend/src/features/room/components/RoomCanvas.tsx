import { useEffect, useRef } from "react";

import { RoomRuntime, type RoomRenderer } from "../runtime/RoomRuntime";
import type { RoomState } from "../model/room";

interface RoomCanvasProps {
  state: RoomState;
  editing: boolean;
  /** Injected so this component never imports Pixi directly and stays testable. */
  createRenderer: () => RoomRenderer;
}

/**
 * React bridge for the room scene. Owns the mount host, a ResizeObserver and
 * exactly one RoomRuntime per effect run; the cleanup always destroys the
 * runtime, so StrictMode double-mounts and unmounts leave no canvas behind.
 * Pixi draws only here — product text, buttons and sheets live in RoomHome.
 */
export function RoomCanvas({ state, editing, createRenderer }: RoomCanvasProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<RoomRuntime | null>(null);
  const stateRef = useRef(state);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const runtime = new RoomRuntime(createRenderer());
    runtimeRef.current = runtime;
    void runtime.mount(host, stateRef.current);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[entries.length - 1];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      if (width > 0 && height > 0) runtime.resize(width, height);
    });
    observer.observe(host);

    return () => {
      observer.disconnect();
      runtimeRef.current = null;
      runtime.destroy();
    };
  }, [createRenderer]);

  useEffect(() => {
    stateRef.current = state;
    runtimeRef.current?.update(state);
  }, [state]);

  useEffect(() => {
    runtimeRef.current?.setEditing(editing);
  }, [editing]);

  return <div className="room-canvas" ref={hostRef} aria-hidden="true" />;
}
