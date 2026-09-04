import { useEffect, useRef } from "react";

import type { RoomCatalog } from "../catalog/roomCatalog";
import type { NormalizedPoint } from "../model/placement";
import type { RoomState } from "../model/room";
import { PixiRoomRenderer } from "../pixi/PixiRoomRenderer";
import { RoomRuntime } from "../runtime/RoomRuntime";

export interface RoomCanvasProps {
  state: RoomState;
  catalog: RoomCatalog;
  editing: boolean;
  onItemMove: (id: string, position: NormalizedPoint) => void;
}

export function RoomCanvas({ state, catalog, editing, onItemMove }: RoomCanvasProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<RoomRuntime | null>(null);
  const stateRef = useRef(state);
  const editingRef = useRef(editing);
  const moveRef = useRef(onItemMove);

  useEffect(() => {
    stateRef.current = state;
    runtimeRef.current?.update(state);
  }, [state]);

  useEffect(() => {
    editingRef.current = editing;
    runtimeRef.current?.setEditing(editing);
  }, [editing]);

  useEffect(() => {
    moveRef.current = onItemMove;
  }, [onItemMove]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const runtime = new RoomRuntime(new PixiRoomRenderer(catalog, (id, position) => {
      moveRef.current(id, position);
    }));
    runtimeRef.current = runtime;
    const observer = new ResizeObserver(([entry]) => {
      if (entry) runtime.resize(entry.contentRect.width, entry.contentRect.height);
    });
    observer.observe(host);
    void runtime.mount(host, stateRef.current).then(() => {
      runtime.setEditing(editingRef.current);
    }).catch(() => runtime.destroy());
    return () => {
      observer.disconnect();
      runtime.destroy();
      if (runtimeRef.current === runtime) runtimeRef.current = null;
    };
  }, [catalog]);

  return <div ref={hostRef} className="room-canvas" aria-hidden="true" />;
}
