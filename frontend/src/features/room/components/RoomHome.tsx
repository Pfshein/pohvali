import { useMemo, useState } from "react";

import { createRoomCatalog, type RoomMascotAsset } from "../catalog/roomCatalog";
import { createStarterRoom } from "../catalog/starterRoom";
import type { NormalizedPoint } from "../model/placement";
import { moveRoomItem } from "../model/room";
import { RoomCanvas } from "./RoomCanvas";

export interface RoomHomeProps {
  mascot: RoomMascotAsset;
  onPraise: () => void;
  onOpenCalendar: () => void;
  onOpenProfile: () => void;
}

export function RoomHome({
  mascot,
  onPraise,
  onOpenCalendar,
  onOpenProfile,
}: RoomHomeProps) {
  const { code, label, assetPath } = mascot;
  const catalog = useMemo(
    () => createRoomCatalog([{ code, label, assetPath }]),
    [assetPath, code, label],
  );
  const starterRoom = useMemo(() => createStarterRoom(code, catalog), [catalog, code]);
  const [positions, setPositions] = useState<Readonly<Record<string, NormalizedPoint>>>({});
  const room = useMemo(() => ({
    ...starterRoom,
    items: starterRoom.items.map((item) => ({
      ...item,
      position: positions[item.id] ?? item.position,
    })),
  }), [positions, starterRoom]);
  const [editing, setEditing] = useState(false);

  function moveItem(id: string, position: NormalizedPoint) {
    const moved = moveRoomItem(room, id, position);
    const movedItem = moved.items.find((item) => item.id === id);
    if (movedItem) setPositions((current) => ({ ...current, [id]: movedItem.position }));
  }

  return (
    <section className="room-home" aria-label="Комната">
      <RoomCanvas state={room} catalog={catalog} editing={editing} onItemMove={moveItem} />
      <nav className="room-home__utility" aria-label="Разделы приложения">
        <button type="button" className="room-home__icon" aria-label="Открыть календарь" onClick={onOpenCalendar}>
          <span aria-hidden="true">▦</span>
        </button>
        <button type="button" className="room-home__icon" aria-label="Открыть профиль" onClick={onOpenProfile}>
          <span aria-hidden="true">●</span>
        </button>
      </nav>
      <div className="room-home__actions">
        <button type="button" className="primary-button room-home__praise" onClick={onPraise}>
          Похвалить себя
        </button>
        <button
          type="button"
          className="room-home__furnish"
          aria-pressed={editing}
          onClick={() => setEditing((value) => !value)}
        >
          {editing ? "Готово" : "Обустроить"}
        </button>
      </div>
    </section>
  );
}
