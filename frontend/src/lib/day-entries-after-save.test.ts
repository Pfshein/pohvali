import { describe, expect, it } from "vitest";

import type { PraiseCreated } from "./api";
import { dayEntriesAfterSave, type DayEntry } from "./praise-api";

function created(overrides: Partial<PraiseCreated> = {}): PraiseCreated {
  return {
    id: "new-1",
    local_date: "2026-09-02",
    star_awarded: true,
    balance: 5,
    newly_unlocked: [],
    ...overrides,
  };
}

function entry(overrides: Partial<DayEntry> = {}): DayEntry {
  return {
    id: "old-1",
    local_date: "2026-09-02",
    created_at: "2026-09-02T08:00:00Z",
    text: "Раньше",
    unreadable: false,
    ...overrides,
  };
}

describe("day entries after saving a praise", () => {
  it("shows a praise saved for the open day without a reload", () => {
    const entries = dayEntriesAfterSave(
      [],
      "2026-09-02",
      created(),
      "Вовремя остановился",
      "2026-09-02T09:00:00Z",
    );

    expect(entries).toEqual([
      {
        id: "new-1",
        local_date: "2026-09-02",
        created_at: "2026-09-02T09:00:00Z",
        text: "Вовремя остановился",
        unreadable: false,
      },
    ]);
  });

  it("keeps the day oldest first, the way a reload returns it", () => {
    const entries = dayEntriesAfterSave(
      [entry()],
      "2026-09-02",
      created(),
      "Позже",
      "2026-09-02T09:00:00Z",
    );

    expect(entries?.map((item) => item.id)).toEqual(["old-1", "new-1"]);
  });

  it("leaves another open day untouched", () => {
    const open = [entry({ id: "other", local_date: "2026-09-01" })];

    expect(dayEntriesAfterSave(open, "2026-09-01", created(), "Сегодня")).toBe(open);
  });

  it("stays out of the way while the day is still loading", () => {
    expect(dayEntriesAfterSave(null, "2026-09-02", created(), "Сегодня")).toBeNull();
  });

  it("does not duplicate an entry the reload already brought in", () => {
    const open = [entry({ id: "new-1" })];

    expect(dayEntriesAfterSave(open, "2026-09-02", created(), "Сегодня")).toBe(open);
  });

  it("adds nothing when no day is open", () => {
    expect(dayEntriesAfterSave([], null, created(), "Сегодня")).toEqual([]);
  });
});
