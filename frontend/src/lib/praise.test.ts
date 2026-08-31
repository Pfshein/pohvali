import { describe, expect, it } from "vitest";

import { isValidPraise, normalizePraise } from "./praise";

describe("praise validation", () => {
  it("accepts a small everyday praise", () => {
    expect(isValidPraise("Встал и умылся")).toBe(true);
  });

  it.each(["", "   ", "1234", "!!!?", "я", "  да  "])("rejects %j", (value) => {
    expect(isValidPraise(value)).toBe(false);
  });

  it("supports Unicode letters and trims whitespace", () => {
    expect(isValidPraise("  сделал чай ☕  ")).toBe(true);
    expect(normalizePraise("  сделал чай ☕  ")).toBe("сделал чай ☕");
  });

  it("rejects more than 500 characters", () => {
    expect(isValidPraise("а".repeat(501))).toBe(false);
  });
});

