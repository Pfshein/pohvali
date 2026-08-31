import { describe, expect, it } from "vitest";

import { buildMonthStarArc } from "./month-progress";

describe("buildMonthStarArc", () => {
  it("fills the actual praised days instead of implying a consecutive streak", () => {
    const praisedDays = new Set([2, 5, 9, 14, 18, 23, 27]);

    const stars = buildMonthStarArc(praisedDays, 31);

    expect(stars).toHaveLength(31);
    expect(stars.filter((star) => star.filled).map((star) => star.day)).toEqual([
      2, 5, 9, 14, 18, 23, 27,
    ]);
  });

  it.each([28, 29, 30, 31])("supports a %s-day month", (daysInMonth) => {
    expect(buildMonthStarArc(new Set([daysInMonth]), daysInMonth)).toHaveLength(daysInMonth);
  });

  it("clamps invalid month lengths and ignores out-of-range praise days", () => {
    const stars = buildMonthStarArc(new Set([0, 1, 31, 32]), 42);

    expect(stars).toHaveLength(31);
    expect(stars.filter((star) => star.filled).map((star) => star.day)).toEqual([1, 31]);
  });
});
