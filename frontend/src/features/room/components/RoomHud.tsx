import { RoomSettingsIcon, RoomSparkIcon } from "./RoomIcons";
import { roomProgressCaption } from "./roomProgress";

interface RoomHudProps {
  praisedDayCount: number;
  onOpenSettings: () => void;
}

export function RoomHud({ praisedDayCount, onOpenSettings }: RoomHudProps) {
  const caption = roomProgressCaption(praisedDayCount);

  return (
    <div className="room-hud">
      <div className="room-hud__progress" aria-live="polite" aria-label={`В этом месяце: ${caption}`}>
        <RoomSparkIcon />
        <span>{caption}</span>
      </div>
      <button
        type="button"
        className="room-hud__settings"
        aria-label="Открыть настройки"
        onClick={onOpenSettings}
      >
        <RoomSettingsIcon />
      </button>
    </div>
  );
}
