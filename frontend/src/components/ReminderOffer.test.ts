import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ReminderOffer } from "./ReminderOffer";

const FORBIDDEN_TONE_WORDS = [
  "серия",
  "серию",
  "пропустил",
  "пропущен",
  "не потеряй",
  "не теряй",
  "подряд",
];

describe("reminder offer", () => {
  it("asks calmly with both choices and does not answer on its own", () => {
    const onAnswer = vi.fn(async () => {});

    const markup = renderToStaticMarkup(
      createElement(ReminderOffer, { onAnswer }),
    );

    expect(markup).toContain("напоминание");
    expect(markup).toContain("Да, напоминай");
    expect(markup).toContain("Не нужно");
    expect(markup).not.toContain("запис");  // never mentions personal entries
    const lowered = markup.toLowerCase();
    for (const word of FORBIDDEN_TONE_WORDS) {
      expect(lowered).not.toContain(word);
    }
    expect(onAnswer).not.toHaveBeenCalled();
  });

  it("does not claim a specific promise beyond one quiet evening message", () => {
    const markup = renderToStaticMarkup(
      createElement(ReminderOffer, { onAnswer: vi.fn(async () => {}) }),
    );

    expect(markup).toContain("Около 22:00");
    expect(markup).toContain("в любой момент");
  });
});
