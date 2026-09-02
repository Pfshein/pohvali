import { describe, expect, it } from "vitest";

import { monthStarsCaption, pluralRu, starsWithCount } from "./plural";

describe("russian pluralisation", () => {
  it("picks the right form across the whole range", () => {
    const form = (n: number) => pluralRu(n, "звезда", "звезды", "звёзд");

    expect([1, 21, 101].map(form)).toEqual(["звезда", "звезда", "звезда"]);
    expect([2, 3, 4, 22, 34].map(form)).toEqual(
      ["звезды", "звезды", "звезды", "звезды", "звезды"],
    );
    expect([0, 5, 9, 20, 25].map(form)).toEqual(
      ["звёзд", "звёзд", "звёзд", "звёзд", "звёзд"],
    );
    // The teens are the case a naive "n % 10" rule gets wrong.
    expect([11, 12, 13, 14, 111].map(form)).toEqual(
      ["звёзд", "звёзд", "звёзд", "звёзд", "звёзд"],
    );
  });

  it("counts stars without the '1 звёзд' wording", () => {
    expect(starsWithCount(1)).toBe("1 звезда");
    expect(starsWithCount(3)).toBe("3 звезды");
    expect(starsWithCount(5)).toBe("5 звёзд");
    expect(starsWithCount(21)).toBe("21 звезда");
    expect(starsWithCount(0)).toBe("0 звёзд");
  });
});

describe("month caption under the mascot", () => {
  it("names what the stars mean and never the mascot", () => {
    expect(monthStarsCaption(1, "сентябре"))
      .toBe("1 звезда в сентябре — момент, когда ты выбираешь себя");
    expect(monthStarsCaption(5, "сентябре"))
      .toBe("5 звёзд в сентябре — моменты, когда ты выбираешь себя");
    expect(monthStarsCaption(21, "сентябре"))
      .toBe("21 звезда в сентябре — моменты, когда ты выбираешь себя");
  });

  it("stays calm and inviting on an empty month", () => {
    const caption = monthStarsCaption(0, "сентябре");

    expect(caption).toBe("В сентябре пока тихо. Первая звезда впереди");
    // No count of zero, and nothing that reads as a reproach.
    expect(caption).not.toContain("0");
  });

  it("uses no gendered verb forms, so it fits every reader", () => {
    const captions = [0, 1, 2, 5, 11, 21].map((n) => monthStarsCaption(n, "сентябре"));

    for (const caption of captions) {
      expect(caption).not.toMatch(/(дал|дала|выбрал|выбрала|был|была)\b/);
    }
  });
});
