import { useEffect, useMemo, useState } from "react";

import { CollectionPanel } from "./components/CollectionPanel";
import { MonthCalendar } from "./components/MonthCalendar";
import { PrivacyPanel } from "./components/PrivacyPanel";
import { RecoveryAccess } from "./components/RecoveryAccess";
import { StarArcHero } from "./components/StarArcHero";
import type { PraiseCreated } from "./lib/api";
import {
  currentMonth,
  dateInMonth,
  markedDaysForMonth,
  monthRange,
  type CalendarDay,
  type MonthRef,
} from "./lib/calendar";
import { findMascot, unlockedMascotMessage } from "./lib/mascots";
import type { MascotCollection, PurchaseOutcome } from "./lib/mascots-api";
import { russianMonthNameGenitive, russianMonthNamePrepositional } from "./lib/month-grid";
import type { DayEntry } from "./lib/praise-api";
import { isValidPraise, MAX_PRAISE_LENGTH, normalizePraise } from "./lib/praise";

function shiftMonth(current: MonthRef, delta: number): MonthRef {
  const zeroBased = current.month - 1 + delta;
  return {
    year: current.year + Math.floor(zeroBased / 12),
    month: ((zeroBased % 12) + 12) % 12 + 1,
  };
}

export interface MascotCollectionHandlers {
  load: () => Promise<MascotCollection>;
  purchase: (code: string) => Promise<PurchaseOutcome>;
  activate: (code: string) => Promise<void>;
}

export interface AppProps {
  firstName?: string;
  mascotCode?: string;
  onSubmitPraise?: (text: string) => Promise<PraiseCreated>;
  onExportRecoveryPhrase?: () => Promise<string>;
  onImportRecoveryPhrase?: (phrase: string) => Promise<void>;
  onDeleteAccount?: () => Promise<void>;
  mascotCollection?: MascotCollectionHandlers;
  onLoadCalendar?: (from: string, to: string) => Promise<CalendarDay[]>;
  onLoadDay?: (date: string) => Promise<DayEntry[]>;
  initialViewMonth?: MonthRef;
  initialBalance?: number | null;
  initialCalendarDays?: CalendarDay[];
}

export function App({
  firstName,
  mascotCode,
  onSubmitPraise,
  onExportRecoveryPhrase,
  onImportRecoveryPhrase,
  onDeleteAccount,
  mascotCollection,
  onLoadCalendar,
  onLoadDay,
  initialViewMonth,
  initialBalance = null,
  initialCalendarDays = [],
}: AppProps = {}) {
  const [activeMascotCode, setActiveMascotCode] = useState(mascotCode);
  const mascot = findMascot(activeMascotCode);
  const [isComposerOpen, setComposerOpen] = useState(false);
  const [isCollectionOpen, setCollectionOpen] = useState(false);
  const [praise, setPraise] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [isSaving, setSaving] = useState(false);
  const [viewMonth, setViewMonth] = useState(initialViewMonth ?? currentMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [calendarDays, setCalendarDays] = useState<CalendarDay[]>(initialCalendarDays);
  const [calendarError, setCalendarError] = useState(false);
  const [balance, setBalance] = useState<number | null>(initialBalance);
  const [dayEntries, setDayEntries] = useState<DayEntry[] | null>(null);
  const [dayError, setDayError] = useState(false);
  const canSave = isValidPraise(praise);

  const markedDays = useMemo(
    () => markedDaysForMonth(calendarDays, viewMonth),
    [calendarDays, viewMonth],
  );
  const daysInMonth = new Date(viewMonth.year, viewMonth.month, 0).getDate();

  const liveCollection = useMemo<MascotCollectionHandlers | undefined>(() => {
    if (!mascotCollection) return undefined;
    return {
      load: async () => {
        const collection = await mascotCollection.load();
        setBalance(collection.balance);
        if (collection.activeMascot) setActiveMascotCode(collection.activeMascot);
        return collection;
      },
      purchase: async (code) => {
        const result = await mascotCollection.purchase(code);
        setBalance(result.balance);
        return result;
      },
      activate: async (code) => {
        await mascotCollection.activate(code);
        setActiveMascotCode(code);
      },
    };
  }, [mascotCollection]);

  useEffect(() => {
    if (!liveCollection) return;
    void liveCollection.load().catch(() => undefined);
  }, [liveCollection]);

  useEffect(() => {
    if (!onLoadCalendar) return;
    let active = true;
    const range = monthRange(viewMonth);
    void onLoadCalendar(range.from, range.to)
      .then((days) => {
        if (active) {
          setCalendarDays(days);
          setCalendarError(false);
        }
      })
      .catch(() => {
        if (active) {
          setCalendarDays([]);
          setCalendarError(true);
        }
      });
    return () => {
      active = false;
    };
  }, [onLoadCalendar, viewMonth]);

  useEffect(() => {
    if (selectedDay === null || !onLoadDay) return;
    let active = true;
    void onLoadDay(dateInMonth(viewMonth, selectedDay))
      .then((entries) => {
        if (active) {
          setDayEntries(entries);
          setDayError(false);
        }
      })
      .catch(() => {
        if (active) setDayError(true);
      });
    return () => {
      active = false;
    };
  }, [onLoadDay, selectedDay, viewMonth]);

  function goToMonth(delta: number) {
    setViewMonth((current) => shiftMonth(current, delta));
    setSelectedDay(null);
    setDayEntries(null);
    setDayError(false);
    setCalendarError(false);
  }

  function selectDay(day: number) {
    setSelectedDay(day);
    setDayEntries(null);
    setDayError(false);
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
      setBalance(result.balance);
      setCalendarDays((days) => {
        const existing = days.find((day) => day.localDate === result.local_date);
        if (!existing) return [...days, { localDate: result.local_date, count: 1 }];
        return days.map((day) => day.localDate === result.local_date
          ? { ...day, count: day.count + 1 }
          : day);
      });
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
        <div
          className="star-balance"
          aria-label={balance === null ? "Баланс загружается" : `${balance} звёзд`}
        >
          <span aria-hidden="true">★</span><b>{balance ?? "…"}</b>
        </div>
      </header>

      <StarArcHero
        praisedDays={markedDays}
        monthName={russianMonthNamePrepositional(viewMonth.month)}
        daysInMonth={daysInMonth}
        mascot={mascot}
      />

      <MonthCalendar
        year={viewMonth.year}
        month={viewMonth.month}
        markedDays={markedDays}
        selectedDay={selectedDay}
        onSelectDay={selectDay}
        onPrevMonth={() => goToMonth(-1)}
        onNextMonth={() => goToMonth(1)}
      />

      {calendarError && (
        <p className="inline-note" role="status">
          Не удалось обновить календарь. Можно листать дальше и попробовать ещё раз.
        </p>
      )}

      {selectedDay !== null && onLoadDay && (
        <section className="day-praises" aria-live="polite">
          <h2>Похвалы за {selectedDay} {russianMonthNameGenitive(viewMonth.month)}</h2>
          {dayError ? (
            <p>Не удалось открыть записи этого дня.</p>
          ) : dayEntries === null ? (
            <p>Открываем записи…</p>
          ) : dayEntries.length === 0 ? (
            <p>В этот день записей нет.</p>
          ) : (
            <ul>
              {dayEntries.map((entry) => (
                <li key={entry.id}>
                  {entry.unreadable ? "Не удалось расшифровать эту запись." : entry.text}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="gentle-prompt">
        <div>
          <p className="eyebrow">Можно даже за мелочь</p>
          <h2>За что ты хочешь похвалить себя сегодня?</h2>
        </div>
        <button className="primary-button" onClick={() => setComposerOpen(true)}>
          Написать
        </button>
      </section>

      {mascotCollection && (
        <section className="collection-entry">
          <button
            className="secondary-button"
            aria-expanded={isCollectionOpen}
            onClick={() => setCollectionOpen((open) => !open)}
          >
            {isCollectionOpen ? "Свернуть коллекцию" : "Коллекция спутников"}
          </button>
          {isCollectionOpen && liveCollection && (
            <CollectionPanel
              load={liveCollection.load}
              purchase={liveCollection.purchase}
              activate={liveCollection.activate}
            />
          )}
        </section>
      )}

      <p className="privacy-note">🔒 Текст шифруется на этом устройстве до отправки.</p>
      {onExportRecoveryPhrase && onImportRecoveryPhrase && (
        <RecoveryAccess
          onExport={onExportRecoveryPhrase}
          onImport={onImportRecoveryPhrase}
        />
      )}
      {onDeleteAccount && <PrivacyPanel onDeleteAccount={onDeleteAccount} />}

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
