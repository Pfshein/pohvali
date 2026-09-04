import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App, type AppProps } from "./App";

const ROOM_PREFERENCE = JSON.stringify({ schemaVersion: 1, mode: "room" });

function stubWindow(options: { roomPreference?: boolean } = {}) {
  vi.stubGlobal("window", {
    Telegram: undefined,
    localStorage: {
      getItem: () => (options.roomPreference ? ROOM_PREFERENCE : null),
      setItem: () => undefined,
    },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("home screen rewards hero", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders star currency and a monthly avocado progress hero", () => {
    vi.stubGlobal("window", { Telegram: undefined });

    const markup = renderToStaticMarkup(createElement<AppProps>(App, {
      initialViewMonth: { year: 2026, month: 9 },
      initialBalance: 4,
      initialCalendarDays: [
        { localDate: "2026-09-02", count: 1 },
        { localDate: "2026-09-18", count: 2 },
      ],
    }));

    expect(markup).toContain('aria-label="4 звезды"');
    expect(markup).toContain('alt="Авокадо Ава — талисман приложения"');
    expect(markup).toContain("2 звезды в сентябре — моменты, когда ты выбираешь себя");

    // The caption says what the stars mean; the mascot keeps the reader
    // company but is not named there.
    const caption = markup.match(/<div class="mascot-hero__caption">.*?<\/div>/s)?.[0] ?? "";
    expect(caption).toContain("моменты, когда ты выбираешь себя");
    expect(caption).not.toContain("Ава");
    expect(markup.match(/class="arc-star/g)).toHaveLength(30);
    expect(markup.match(/arc-star--filled/g)).toHaveLength(2);
    expect(markup).not.toContain('aria-label="12 звёзд"');
    expect(markup).not.toContain("печен");
  });

  it("offers the reversible switch to the room design without a canvas", () => {
    vi.stubGlobal("window", { Telegram: undefined });

    const markup = renderToStaticMarkup(createElement<AppProps>(App, {
      initialViewMonth: { year: 2026, month: 9 },
    }));

    expect(markup).toContain(">Новый дизайн<");
    expect(markup).not.toContain("<canvas");
  });

  it("puts the invitation to write above the calendar", () => {    vi.stubGlobal("window", { Telegram: undefined });

    const markup = renderToStaticMarkup(createElement<AppProps>(App, {
      initialViewMonth: { year: 2026, month: 9 },
    }));

    // Writing a praise is the point of the screen; the calendar looks back on
    // it, so it follows rather than leads.
    const prompt = markup.indexOf('class="gentle-prompt"');
    const calendar = markup.indexOf('class="calendar"');
    const hero = markup.indexOf('class="mascot-hero"');

    expect(prompt).toBeGreaterThan(-1);
    expect(calendar).toBeGreaterThan(-1);
    expect(hero).toBeLessThan(prompt);
    expect(prompt).toBeLessThan(calendar);
  });
});

describe("reversible room UI switch", () => {
  it("keeps classic as the default presentation", () => {
    stubWindow();

    const markup = renderToStaticMarkup(createElement<AppProps>(App, {
      initialViewMonth: { year: 2026, month: 9 },
    }));

    expect(markup).toContain(">Новый дизайн<");
    expect(markup).toContain('class="mascot-hero"');
    expect(markup).not.toContain("Открываем комнату");
  });

  it("shows a recoverable loading state instead of classic when room is chosen", () => {
    stubWindow({ roomPreference: true });

    const markup = renderToStaticMarkup(createElement<AppProps>(App, {
      initialViewMonth: { year: 2026, month: 9 },
    }));

    expect(markup).toContain("Открываем комнату…");
    expect(markup).toContain(">Вернуться в старый UI<");
    expect(markup).not.toContain('class="mascot-hero"');
    expect(markup).not.toContain("<canvas");
  });
});
