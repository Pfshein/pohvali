import { useState } from "react";

import { MonthCalendar } from "./components/MonthCalendar";
import { RecoveryAccess } from "./components/RecoveryAccess";
import { StarArcHero } from "./components/StarArcHero";
import type { PraiseCreated } from "./lib/api";
import { findMascot, unlockedMascotMessage } from "./lib/mascots";
import { isValidPraise, MAX_PRAISE_LENGTH, normalizePraise } from "./lib/praise";

const PRAISED_DAYS = new Set([2, 5, 9, 14, 18, 23, 27]);
const PRAISED_MONTH = { year: 2026, month: 8 };
const NO_MARKED_DAYS: ReadonlySet<number> = new Set();

function shiftMonth(current: { year: number; month: number }, delta: number): {
  year: number;
  month: number;
} {
  const zeroBased = current.month - 1 + delta;
  return {
    year: current.year + Math.floor(zeroBased / 12),
    month: ((zeroBased % 12) + 12) % 12 + 1,
  };
}

interface AppProps {
  firstName?: string;
  mascotCode?: string;
  onSubmitPraise?: (text: string) => Promise<PraiseCreated>;
  onExportRecoveryPhrase?: () => Promise<string>;
  onImportRecoveryPhrase?: (phrase: string) => Promise<void>;
}

export function App({
  firstName,
  mascotCode,
  onSubmitPraise,
  onExportRecoveryPhrase,
  onImportRecoveryPhrase,
}: AppProps = {}) {
  const mascot = findMascot(mascotCode);
  const [isComposerOpen, setComposerOpen] = useState(false);
  const [praise, setPraise] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [isSaving, setSaving] = useState(false);
  const [viewMonth, setViewMonth] = useState(PRAISED_MONTH);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const canSave = isValidPraise(praise);

  const markedDays =
    viewMonth.year === PRAISED_MONTH.year && viewMonth.month === PRAISED_MONTH.month
      ? PRAISED_DAYS
      : NO_MARKED_DAYS;

  function goToMonth(delta: number) {
    setViewMonth((current) => shiftMonth(current, delta));
    setSelectedDay(null);
  }

  async function handleSave() {
    if (!canSave || isSaving) return;
    const text = normalizePraise(praise);

    if (!onSubmitPraise) {
      setSavedMessage(`Сохранили: «${text}»`);
      setPraise("");
      setComposerOpen(false);
      window.setTimeout(() => setSavedMessage(""), 2600);
      return;
    }

    setSaving(true);
    try {
      const result = await onSubmitPraise(text);
      setSavedMessage(unlockedMascotMessage(result.newly_unlocked) ?? "Сохранили ⭐");
      setPraise("");
      setComposerOpen(false);
    } catch {
      setSavedMessage("Не удалось сохранить. Можно попробовать ещё раз.");
    } finally {
      setSaving(false);
      window.setTimeout(() => setSavedMessage(""), 2600);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Тихое место на сегодня</p>
          <h1>{firstName ? `${firstName}, привет` : "Похвали себя"}</h1>
        </div>
        <div className="star-balance" aria-label="12 звёзд"><span aria-hidden="true">★</span><b>12</b></div>
      </header>

      <StarArcHero
        praisedDays={PRAISED_DAYS}
        monthName="августе"
        daysInMonth={31}
        mascot={mascot}
      />

      <MonthCalendar
        year={viewMonth.year}
        month={viewMonth.month}
        markedDays={markedDays}
        selectedDay={selectedDay}
        onSelectDay={setSelectedDay}
        onPrevMonth={() => goToMonth(-1)}
        onNextMonth={() => goToMonth(1)}
      />

      <section className="gentle-prompt">
        <div>
          <p className="eyebrow">Можно даже за мелочь</p>
          <h2>За что ты хочешь похвалить себя сегодня?</h2>
        </div>
        <button className="primary-button" onClick={() => setComposerOpen(true)}>
          Написать
        </button>
      </section>

      <p className="privacy-note">🔒 Текст шифруется на этом устройстве до отправки.</p>
      {onExportRecoveryPhrase && onImportRecoveryPhrase && (
        <RecoveryAccess
          onExport={onExportRecoveryPhrase}
          onImport={onImportRecoveryPhrase}
        />
      )}

      {isComposerOpen && (
        <div className="scrim" role="presentation" onMouseDown={() => setComposerOpen(false)}>
          <section
            className="composer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="composer-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="composer__handle" />
            <button className="composer__close" onClick={() => setComposerOpen(false)} aria-label="Закрыть">×</button>
            <p className="eyebrow">Сегодня</p>
            <h2 id="composer-title">Похвала тоже считается</h2>
            <textarea
              autoFocus
              maxLength={MAX_PRAISE_LENGTH}
              value={praise}
              onChange={(event) => setPraise(event.target.value)}
              placeholder="Например: вовремя остановился и отдохнул"
              aria-describedby="composer-help"
            />
            <div className="composer__meta" id="composer-help">
              <span>Только ты сможешь это прочитать</span>
              <span>{praise.length}/{MAX_PRAISE_LENGTH}</span>
            </div>
            <button
              className="primary-button primary-button--wide"
              disabled={!canSave || isSaving}
              onClick={() => void handleSave()}
            >
              {isSaving ? "Сохраняем…" : "Сохранить похвалу"}
            </button>
          </section>
        </div>
      )}

      {savedMessage && <div className="toast" role="status">{savedMessage}</div>}
    </main>
  );
}
