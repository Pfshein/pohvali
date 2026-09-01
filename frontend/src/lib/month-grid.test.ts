import { describe, expect, it } from "vitest";

import {
  buildMonthGrid,
  daysInMonth,
  russianMonthName,
  russianMonthNamePrepositional,
} from "./month-grid";

describe("daysInMonth", () => {
  it.each([
    [2026, 1, 31],
    [2026, 2, 28],
    [2024, 2, 29],
    [2026, 4, 30],
    [2026, 9, 30],
  ])("year %i month %i has %i days", (year, month, expected) => {
    expect(daysInMonth(year, month)).toBe(expected);
  });
});

describe("buildMonthGrid", () => {
  it.each([
    [2026, 2],
    [2024, 2],
    [2026, 4],
    [2026, 1],
  ])("keeps every day and pads weeks to 7 for %i-%i", (year, month) => {
    const grid = buildMonthGrid(year, month, new Set());

    const cells = grid.weeks.flat();
    const days = cells.filter((cell) => cell !== null).map((cell) => cell!.day);

    expect(days).toEqual(Array.from({ length: daysInMonth(year, month) }, (_, i) => i + 1));
    expect(grid.weeks.every((week) => week.length === 7)).toBe(true);
  });

  it("places a Monday-first leading offset before day one", () => {
    // 2026-09-01 is a Tuesday → one leading blank in a Monday-first grid.
    const grid = buildMonthGrid(2026, 9, new Set());
    const firstWeek = grid.weeks[0]!;

    expect(firstWeek[0]).toBeNull();
    expect(firstWeek[1]).toEqual({ day: 1, marked: false });
  });

  it("marks days and counts each marked day once, ignoring out-of-range", () => {
    const grid = buildMonthGrid(2026, 9, new Set([1, 3, 3, 0, 40]));

    expect(grid.markedCount).toBe(2);
    const marked = grid.weeks.flat().filter((cell) => cell?.marked).map((cell) => cell!.day);
    expect(marked).toEqual([1, 3]);
  });
});

describe("russianMonthName", () => {
  it("returns the nominative month name", () => {
    expect(russianMonthName(9)).toBe("Сентябрь");
    expect(russianMonthName(8)).toBe("Август");
  });

  it("returns the prepositional month name for progress copy", () => {
    expect(russianMonthNamePrepositional(9)).toBe("сентябре");
  });
});
