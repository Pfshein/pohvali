export interface MonthCell {
  day: number;
  marked: boolean;
}

export interface MonthGrid {
  year: number;
  month: number;
  weeks: (MonthCell | null)[][];
  markedCount: number;
}

const MONTH_NAMES = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

const MONTH_NAMES_GENITIVE = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
];

const MONTH_NAMES_PREPOSITIONAL = [
  "январе",
  "феврале",
  "марте",
  "апреле",
  "мае",
  "июне",
  "июле",
  "августе",
  "сентябре",
  "октябре",
  "ноябре",
  "декабре",
];

export function russianMonthName(month: number): string {
  return MONTH_NAMES[month - 1] ?? "";
}

export function russianMonthNameGenitive(month: number): string {
  return MONTH_NAMES_GENITIVE[month - 1] ?? "";
}

export function russianMonthNamePrepositional(month: number): string {
  return MONTH_NAMES_PREPOSITIONAL[month - 1] ?? "";
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function mondayFirstOffset(year: number, month: number): number {
  const jsWeekday = new Date(year, month - 1, 1).getDay();
  return (jsWeekday + 6) % 7;
}

export function buildMonthGrid(
  year: number,
  month: number,
  markedDays: ReadonlySet<number>,
): MonthGrid {
  const total = daysInMonth(year, month);
  const cells: (MonthCell | null)[] = [];

  for (let blank = 0; blank < mondayFirstOffset(year, month); blank += 1) {
    cells.push(null);
  }

  let markedCount = 0;
  for (let day = 1; day <= total; day += 1) {
    const marked = markedDays.has(day);
    if (marked) markedCount += 1;
    cells.push({ day, marked });
  }

  while (cells.length % 7 !== 0) cells.push(null);

  const weeks: (MonthCell | null)[][] = [];
  for (let index = 0; index < cells.length; index += 7) {
    weeks.push(cells.slice(index, index + 7));
  }

  return { year, month, weeks, markedCount };
}
