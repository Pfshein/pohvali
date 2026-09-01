import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ReminderSettings } from "./ReminderSettings";

function controls() {
  return {
    load: vi.fn(async () => ({ enabled: true, dmAvailable: true })),
    setEnabled: vi.fn(async () => ({ enabled: true, dmAvailable: true })),
  };
}

describe("reminder settings", () => {
  it("reflects the enabled state in an accessible switch", () => {
    const markup = renderToStaticMarkup(createElement(ReminderSettings, {
      controls: controls(),
      initialSettings: { enabled: true, dmAvailable: true },
    }));

    expect(markup).toContain('aria-checked="true"');
    expect(markup).toContain("Напоминания");
    expect(markup).toContain("Включены");
  });

  it("reflects the disabled state", () => {
    const markup = renderToStaticMarkup(createElement(ReminderSettings, {
      controls: controls(),
      initialSettings: { enabled: false, dmAvailable: true },
    }));

    expect(markup).toContain('aria-checked="false"');
    expect(markup).toContain("Выключены");
  });

  it("explains the bot-chat requirement only when pushes are impossible", () => {
    const markup = renderToStaticMarkup(createElement(ReminderSettings, {
      controls: controls(),
      initialSettings: { enabled: true, dmAvailable: false },
    }));

    expect(markup).toContain("открыть чат с ботом");

    const reachableMarkup = renderToStaticMarkup(createElement(ReminderSettings, {
      controls: controls(),
      initialSettings: { enabled: true, dmAvailable: true },
    }));
    expect(reachableMarkup).not.toContain("открыть чат с ботом");
  });
});
