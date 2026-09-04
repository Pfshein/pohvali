import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RoomHome } from "./RoomHome";

describe("RoomHome", () => {
  it("keeps primary navigation as accessible DOM controls", () => {
    const markup = renderToStaticMarkup(createElement(RoomHome, {
      mascot: { code: "ava", label: "Авокадо Ава", assetPath: "/assets/mascots/ava.png" },
      onPraise: vi.fn(),
      onOpenCalendar: vi.fn(),
      onOpenProfile: vi.fn(),
    }));

    expect(markup).toContain('aria-label="Комната"');
    expect(markup).toContain(">Похвалить себя<");
    expect(markup).toContain(">Обустроить<");
    expect(markup).toContain('aria-label="Открыть календарь"');
    expect(markup).toContain('aria-label="Открыть профиль"');
    expect(markup).toContain('class="room-canvas"');
    expect(markup).not.toContain("<canvas");
  });
});
