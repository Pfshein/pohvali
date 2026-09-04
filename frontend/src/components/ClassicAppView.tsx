import type { ReactNode } from "react";

import { StarArcHero } from "./StarArcHero";
import type { Mascot } from "../lib/mascots";
import { starsWithCount } from "../lib/plural";

/**
 * The pre-room home screen, moved out of App unchanged: same classes, same
 * copy, same section order. App keeps owning the state and passes calendar,
 * profile, composer and status subtrees as slots, so this component stays a
 * pure presentation of the classic design and imports no room code.
 */
export interface ClassicAppViewProps {
  firstName?: string;
  balance: number | null;
  mascot: Mascot;
  markedDays: ReadonlySet<number>;
  monthName: string;
  daysInMonth: number;
  calendarContent: ReactNode;
  profileContent: ReactNode;
  composerContent: ReactNode;
  statusContent: ReactNode;
  onPraise: () => void;
  onSelectRoom: () => void;
}

export function ClassicAppView({
  firstName,
  balance,
  mascot,
  markedDays,
  monthName,
  daysInMonth,
  calendarContent,
  profileContent,
  composerContent,
  statusContent,
  onPraise,
  onSelectRoom,
}: ClassicAppViewProps) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Любовь начинается с себя</p>
          <h1>{firstName ? `${firstName}, привет` : "Похвали себя"}</h1>
        </div>
        <div
          className="star-balance"
          aria-label={balance === null ? "Баланс загружается" : starsWithCount(balance)}
        >
          <span aria-hidden="true">★</span><b>{balance ?? "…"}</b>
        </div>
      </header>

      <StarArcHero
        praisedDays={markedDays}
        monthName={monthName}
        daysInMonth={daysInMonth}
        mascot={mascot}
      />

      <section className="gentle-prompt">
        <div>
          <p className="eyebrow">Можно даже за мелочь</p>
          <h2>За что ты хочешь похвалить себя сегодня?</h2>
        </div>
        <button className="primary-button" onClick={onPraise}>
          Написать
        </button>
      </section>

      {calendarContent}
      {profileContent}

      <button type="button" className="ui-switch" onClick={onSelectRoom}>
        Новый дизайн
      </button>

      {composerContent}
      {statusContent}
    </main>
  );
}
