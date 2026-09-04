import { useCallback, useEffect, useRef } from "react";

import { RoomCanvas } from "./RoomCanvas";
import { RoomBottomNav } from "./RoomBottomNav";
import { RoomFurnishIcon, RoomHeartIcon } from "./RoomIcons";
import { RoomHud } from "./RoomHud";
import { moveRoomItem } from "../model/placement";
import type { RoomItemMoveHandler, RoomState } from "../model/room";
import type { RoomRenderer } from "../runtime/RoomRuntime";
import type { RoomMascotAsset } from "../catalog/roomCatalog";

export type RoomOverlay = "none" | "composer" | "calendar" | "profile" | "settings";

export interface RoomHomeProps {
  mascot: RoomMascotAsset;
  praisedDayCount: number;
  room: RoomState;
  editing: boolean;
  onRoomChange: (state: RoomState) => void;
  onEditingChange: (editing: boolean) => void;
  onOpenOverlay: (overlay: Exclude<RoomOverlay, "none">) => void;
  /** Injected by RoomAppView so this component never imports Pixi directly. */
  createRenderer: (handlers: { onItemMove: RoomItemMoveHandler }) => RoomRenderer;
}

/**
 * The approved first room viewport: DOM HUD, speech bubble, furnish control
 * and bottom navigation around a Pixi scene. React owns every product
 * control; the canvas only draws the room and reports confirmed item moves.
 */
export function RoomHome({
  mascot,
  praisedDayCount,
  room,
  editing,
  onRoomChange,
  onEditingChange,
  onOpenOverlay,
  createRenderer,
}: RoomHomeProps) {
  // Latest-value refs keep the renderer factory stable across renders, so
  // the canvas is not torn down every time the room state changes.
  const roomRef = useRef(room);
  const changeRef = useRef(onRoomChange);
  useEffect(() => {
    roomRef.current = room;
    changeRef.current = onRoomChange;
  });

  const handleItemMove = useCallback<RoomItemMoveHandler>((id, position) => {
    changeRef.current(moveRoomItem(roomRef.current, id, position));
  }, []);

  const createStableRenderer = useCallback(
    () => createRenderer({ onItemMove: handleItemMove }),
    [createRenderer, handleItemMove],
  );

  return (
    <div className="room-home">
      <section
        className="room-home__scene"
        aria-label={`${mascot.name} в уютном кресле`}
      >
        <RoomCanvas state={room} editing={editing} createRenderer={createStableRenderer} />
      </section>

      <RoomHud praisedDayCount={praisedDayCount} onOpenSettings={() => onOpenOverlay("settings")} />

      <div className="room-speech">
        <div className="room-speech__notch" aria-hidden="true">
          <RoomHeartIcon size={16} />
        </div>
        <p className="room-speech__text">За что ты хочешь похвалить себя сегодня?</p>
      </div>

      <div className="room-lower">
        <button
          type="button"
          className="room-furnish"
          aria-pressed={editing}
          onClick={() => onEditingChange(!editing)}
        >
          <RoomFurnishIcon />
          <span>{editing ? "Готово" : "Обустроить"}</span>
        </button>
        <p className="room-tagline">Твой уют начинается<br />с малого шага 🌿</p>
      </div>

      <RoomBottomNav
        onCalendar={() => onOpenOverlay("calendar")}
        onPraise={() => onOpenOverlay("composer")}
        onProfile={() => onOpenOverlay("profile")}
      />
    </div>
  );
}
