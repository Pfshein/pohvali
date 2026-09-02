import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App, type AppProps } from "./App";

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
});
