import { buildMonthGrid, russianMonthName, russianMonthNameGenitive } from "../lib/month-grid";

const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

interface MonthCalendarProps {
  year: number;
  month: number;
  markedDays: ReadonlySet<number>;
  selectedDay: number | null;
  onSelectDay: (day: number) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export function MonthCalendar({
  year,
  month,
  markedDays,
  selectedDay,
  onSelectDay,
  onPrevMonth,
  onNextMonth,
}: MonthCalendarProps) {
  const grid = buildMonthGrid(year, month, markedDays);
  const genitive = russianMonthNameGenitive(month);

  return (
    <section className="calendar" aria-label={`Календарь похвал за ${genitive}`}>
      <div className="calendar__heading">
        <button className="icon-button" aria-label="Предыдущий месяц" onClick={onPrevMonth}>
          ‹
        </button>
        <div>
          <h2>{russianMonthName(month)}</h2>
          <p>⭐ {grid.markedCount} в месяце</p>
        </div>
        <button className="icon-button" aria-label="Следующий месяц" onClick={onNextMonth}>
          ›
        </button>
      </div>
      <div className="calendar__grid calendar__weekdays">
        {WEEKDAYS.map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="calendar__grid calendar__days">
        {grid.weeks.flat().map((cell, index) =>
          cell === null ? (
            <span className="day day--blank" aria-hidden="true" key={`blank-${index}`} />
          ) : (
            <button
              className={cell.marked ? "day day--praised" : "day"}
              key={cell.day}
              aria-label={`${cell.day} ${genitive}${cell.marked ? ", есть похвала" : ""}`}
              aria-pressed={selectedDay === cell.day}
              onClick={() => onSelectDay(cell.day)}
            >
              {cell.day}
              {cell.marked && <span aria-hidden="true">★</span>}
            </button>
          ),
        )}
      </div>
    </section>
  );
}
