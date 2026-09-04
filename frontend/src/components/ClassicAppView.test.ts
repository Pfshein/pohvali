import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ClassicAppView, type ClassicAppViewProps } from "./ClassicAppView";
import { findMascot } from "../lib/mascots";

function renderClassic(overrides: Partial<ClassicAppViewProps> = {}): string {
  const props: ClassicAppViewProps = {
    balance: 3,
    mascot: findMascot("ava"),
    markedDays: new Set([2, 18]),
    monthName: "сентябре",
    daysInMonth: 30,
    calendarContent: createElement("section", { className: "calendar", key: "cal" }, "calendar"),
    profileContent: createElement("section", { className: "collection-entry", key: "prof" }, "profile"),
    composerContent: null,
    statusContent: null,
    onPraise: () => undefined,
    onSelectRoom: () => undefined,
    ...overrides,
  };
  vi.stubGlobal("window", { Telegram: undefined });
  return renderToStaticMarkup(createElement(ClassicAppView, props));
}

describe("ClassicAppView characterization", () => {
  it("keeps the classic structure in the approved order", () => {
    const markup = renderClassic();

    expect(markup).toContain('class="topbar"');
    expect(markup).toContain('class="mascot-hero"');
    expect(markup).toContain('class="gentle-prompt"');

    const topbar = markup.indexOf('class="topbar"');
    const hero = markup.indexOf('class="mascot-hero"');
    const prompt = markup.indexOf('class="gentle-prompt"');
    const calendar = markup.indexOf('class="calendar"');
    const profile = markup.indexOf('class="collection-entry"');
    const switchButton = markup.indexOf(">Новый дизайн<");

    expect(topbar).toBeLessThan(hero);
    expect(hero).toBeLessThan(prompt);
    expect(prompt).toBeLessThan(calendar);
    expect(calendar).toBeLessThan(profile);
    expect(profile).toBeLessThan(switchButton);
  });

  it("shows the star balance and the visible switch to the room UI", () => {
    const markup = renderClassic();

    expect(markup).toContain('aria-label="3 звезды"');
    expect(markup).toContain(">Новый дизайн<");
    expect(markup).toContain('class="ui-switch"');
  });

  it("renders slots for the composer and status content without a canvas", () => {
    const markup = renderClassic({
      composerContent: createElement("div", { className: "scrim", key: "c" }, "composer"),
      statusContent: createElement("div", { className: "toast", key: "t" }, "saved"),
    });

    expect(markup).toContain('class="scrim"');
    expect(markup).toContain('class="toast"');
    expect(markup).not.toContain("<canvas");
  });
});
