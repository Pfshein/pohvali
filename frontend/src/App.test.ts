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

    expect(markup).toContain('aria-label="4 звёзд"');
    expect(markup).toContain('alt="Авокадо Ава — талисман приложения"');
    expect(markup).toContain('aria-label="2 звёзд в сентябре"');
    expect(markup.match(/class="arc-star/g)).toHaveLength(30);
    expect(markup.match(/arc-star--filled/g)).toHaveLength(2);
    expect(markup).not.toContain('aria-label="12 звёзд"');
    expect(markup).not.toContain("печен");
  });
});
