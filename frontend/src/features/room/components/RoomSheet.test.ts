import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { nextFocusableIndex } from "./focusCycle";
import { RoomSheet } from "./RoomSheet";

describe("RoomSheet server markup", () => {
  it("is a labelled modal dialog with a close control and scrim", () => {
    const markup = renderToStaticMarkup(createElement(RoomSheet, {
      title: "Календарь",
      onClose: () => undefined,
      children: createElement("p", null, "content"),
    }));

    expect(markup).toContain('role="dialog"');
    expect(markup).toContain('aria-modal="true"');
    const labelledBy = markup.match(/aria-labelledby="([^"]+)"/)?.[1];
    expect(labelledBy).toBeTruthy();
    expect(markup).toContain(`id="${labelledBy}"`);
    expect(markup).toContain('aria-label="Закрыть"');
    expect(markup).toContain("Календарь");
    expect(markup).toContain("content");
  });
});

describe("focus cycle helper", () => {
  it("wraps Tab and Shift+Tab inside the sheet", () => {
    expect(nextFocusableIndex(0, 3, 1)).toBe(1);
    expect(nextFocusableIndex(2, 3, 1)).toBe(0);
    expect(nextFocusableIndex(0, 3, -1)).toBe(2);
    expect(nextFocusableIndex(1, 3, -1)).toBe(0);
  });

  it("never crashes on an empty focus set", () => {
    expect(nextFocusableIndex(0, 0, 1)).toBe(0);
    expect(nextFocusableIndex(-1, 0, -1)).toBe(-1);
  });
});
