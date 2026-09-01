import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

describe("home screen rewards hero", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders star currency and a monthly avocado progress hero", () => {
    vi.stubGlobal("window", { Telegram: undefined });

    const markup = renderToStaticMarkup(createElement(App));

    expect(markup).toContain('aria-label="12 звёзд"');
    expect(markup).toContain('alt="Авокадо Ава — талисман приложения"');
    expect(markup).toContain('aria-label="7 звёзд в августе"');
    expect(markup.match(/class="arc-star/g)).toHaveLength(31);
    expect(markup.match(/arc-star--filled/g)).toHaveLength(7);
    expect(markup).not.toContain("печен");
  });
});
