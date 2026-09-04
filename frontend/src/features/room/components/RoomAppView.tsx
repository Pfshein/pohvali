import { useCallback, useMemo, useState, type ReactNode } from "react";

import { RoomHome, type RoomOverlay } from "./RoomHome";
import { RoomSheet } from "./RoomSheet";
import { createRoomCatalog, type RoomMascotAsset } from "../catalog/roomCatalog";
import { PixiRoomRenderer } from "../pixi/PixiRoomRenderer";
import type { RoomItemMoveHandler, RoomState } from "../model/room";
import "../room-v2.css";

export interface RoomAppViewProps {
  mascot: RoomMascotAsset;
  praisedDayCount: number;
  room: RoomState;
  onRoomChange: (state: RoomState) => void;
  calendarContent: ReactNode;
  profileContent: ReactNode;
  composerContent: ReactNode;
  statusContent: ReactNode;
  onOpenComposer: () => void;
  onSelectClassic: () => void;
}

/**
 * Shell of the room presentation: it owns the overlay state and sheets while
 * App keeps the business state. Calendars, profile and the composer are the
 * same React nodes classic renders, just hosted in sheets over the room.
 */
export function RoomAppView({
  mascot,
  praisedDayCount,
  room,
  onRoomChange,
  calendarContent,
  profileContent,
  composerContent,
  statusContent,
  onOpenComposer,
  onSelectClassic,
}: RoomAppViewProps) {
  const [overlay, setOverlay] = useState<RoomOverlay>("none");
  const [editing, setEditing] = useState(false);

  const catalog = useMemo(() => createRoomCatalog([mascot]), [mascot]);

  const createRenderer = useCallback(
    ({ onItemMove }: { onItemMove: RoomItemMoveHandler }) =>
      new PixiRoomRenderer({ catalog, onItemMove }),
    [catalog],
  );

  function openOverlay(next: Exclude<RoomOverlay, "none">) {
    if (next === "composer") {
      onOpenComposer();
      return;
    }
    setOverlay(next);
  }

  return (
    <div className="room-root">
      <RoomHome
        mascot={mascot}
        praisedDayCount={praisedDayCount}
        room={room}
        editing={editing}
        onRoomChange={onRoomChange}
        onEditingChange={setEditing}
        onOpenOverlay={openOverlay}
        createRenderer={createRenderer}
      />

      {overlay === "calendar" && (
        <RoomSheet title="Календарь" onClose={() => setOverlay("none")}>
          {calendarContent}
        </RoomSheet>
      )}

      {overlay === "profile" && (
        <RoomSheet title="Профиль" onClose={() => setOverlay("none")}>
          {profileContent}
        </RoomSheet>
      )}

      {overlay === "settings" && (
        <RoomSheet title="Настройки" onClose={() => setOverlay("none")}>
          <div className="room-settings">
            <p className="room-settings__note">
              Комната — это другой вид того же приложения. Похвалы, календарь и
              спутники остаются общими.
            </p>
            <button type="button" className="room-settings__back" onClick={onSelectClassic}>
              Вернуться к старому дизайну
            </button>
          </div>
        </RoomSheet>
      )}

      {composerContent}
      {statusContent}
    </div>
  );
}
