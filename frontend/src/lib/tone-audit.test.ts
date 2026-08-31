import { describe, expect, it } from "vitest";

// Pressure / streak / ranking wording that must never reach a user (PH-604).
const FORBIDDEN = [
  "серия",
  "серию",
  "серий",
  "пропустил",
  "пропущен",
  "не потеряй",
  "не теряй",
  "подряд",
  "streak",
  "рейтинг",
];

const sources = import.meta.glob("/src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function stripComments(code: string): string {
  return code.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
}

describe("tone-of-voice audit", () => {
  it("no user-facing source contains pressure, streak, or ranking wording", () => {
    const offenders: string[] = [];

    for (const [path, code] of Object.entries(sources)) {
      if (path.includes(".test.")) continue;
      const text = stripComments(code).toLowerCase();
      for (const word of FORBIDDEN) {
        if (text.includes(word)) offenders.push(`${path}: ${word}`);
      }
    }

    expect(offenders).toEqual([]);
  });
});
