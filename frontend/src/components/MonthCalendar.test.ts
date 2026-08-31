import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { daysInMonth } from "../lib/month-grid";
import { MonthCalendar } from "./MonthCalendar";

function render(overrides: Partial<Parameters<typeof MonthCalendar>[0]> = {}): string {
  return renderToStaticMarkup(
    createElement(MonthCalendar, {
      year: 2026,
      month: 9,
      markedDays: new Set<number>(),
      selectedDay: null,
      onSelectDay: () => {},
      onPrevMonth: () => {},
      onNextMonth: () => {},
      ...overrides,
    }),
  );
}

describe("MonthCalendar", () => {
  it.each([
    [2026, 2],
    [2024, 2],
    [2026, 4],
    [2026, 1],
  ])("renders one button per day for %i-%i without breaking the grid", (year, month) => {
    const html = render({ year, month });
    const dayButtons = html.match(/aria-label="\d+ /g) ?? [];

    expect(dayButtons).toHaveLength(daysInMonth(year, month));
  });

  it("shows a calm marked-days caption without streak wording", () => {
    const html = render({ markedDays: new Set([2, 5]) });

    expect(html).toContain("⭐ 2 в месяце");
    expect(html).not.toContain("серия");
    expect(html).not.toContain("подряд");
  });

  it("labels marked and selected days for assistive tech", () => {
    const html = render({ markedDays: new Set([3]), selectedDay: 3 });

    expect(html).toContain('aria-label="3 сентября, есть похвала"');
    expect(html).toContain('aria-pressed="true"');
  });

  it("exposes month navigation controls", () => {
    const html = render();

    expect(html).toContain('aria-label="Предыдущий месяц"');
    expect(html).toContain('aria-label="Следующий месяц"');
  });
});
