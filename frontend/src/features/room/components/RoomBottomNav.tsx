import { RoomCalendarIcon, RoomFilledHeartIcon, RoomProfileIcon } from "./RoomIcons";

interface RoomBottomNavProps {
  onCalendar: () => void;
  onPraise: () => void;
  onProfile: () => void;
}

export function RoomBottomNav({ onCalendar, onPraise, onProfile }: RoomBottomNavProps) {
  return (
    <nav className="room-nav" aria-label="Основная навигация">
      <button type="button" className="room-nav__item" aria-label="Открыть календарь" onClick={onCalendar}>
        <RoomCalendarIcon />
        <span>Календарь</span>
      </button>
      <div className="room-nav__cta-slot">
        <button type="button" className="room-nav__cta" aria-label="Похвалить себя" onClick={onPraise}>
          <RoomFilledHeartIcon />
          <span>Похвалить себя</span>
        </button>
      </div>
      <button type="button" className="room-nav__item" aria-label="Открыть профиль" onClick={onProfile}>
        <RoomProfileIcon />
        <span>Профиль</span>
      </button>
    </nav>
  );
}
