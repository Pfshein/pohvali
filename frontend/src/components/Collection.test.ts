import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { MascotItem } from "../lib/mascots-api";
import { Collection } from "./Collection";

function item(overrides: Partial<MascotItem>): MascotItem {
  return {
    code: "tisha",
    name: "Капибара Тиша",
    blurb: "Добрая и невозмутимая",
    assetPath: "/assets/mascots/tisha.png",
    starter: false,
    price: 10,
    state: "affordable",
    unlocked: true,
    active: false,
    ...overrides,
  };
}

function render(mascots: MascotItem[], balance = 12): string {
  return renderToStaticMarkup(
    createElement(Collection, {
      mascots,
      balance,
      busyCode: null,
      onPurchase: () => {},
      onActivate: () => {},
    }),
  );
}

describe("Collection", () => {
  it("shows the spendable balance", () => {
    expect(render([item({})], 7)).toContain('aria-label="7 звёзд"');
  });

  it("marks the active owned mascot without an action button", () => {
    const html = render([
      item({ code: "ava", name: "Ава", state: "owned", active: true, starter: true, price: null }),
    ]);
    expect(html).toContain("Рядом сейчас");
    expect(html).not.toContain("Выбрать");
    expect(html).not.toContain("Открыть за");
  });

  it("offers activation for an owned but inactive mascot", () => {
    const html = render([item({ state: "owned", active: false })]);
    expect(html).toContain("Выбрать");
    expect(html).toContain("Выбрать: Капибара Тиша");
  });

  it("offers a priced purchase for an affordable mascot", () => {
    const html = render([item({ state: "affordable", price: 10 })]);
    expect(html).toContain("Открыть за ⭐10");
    expect(html).toContain("Открыть Капибара Тиша за 10 звёзд");
  });

  it("shows a calm threshold hint for a locked mascot with no purchase control", () => {
    const html = render([
      item({ code: "bim", name: "Бим", state: "locked", unlocked: false, price: 100 }),
    ]);
    expect(html).toContain("Появится ближе к ⭐100");
    expect(html).not.toContain("Открыть за");
  });

  it("nudges gently when unlocked but not yet affordable", () => {
    const html = render([item({ state: "locked", unlocked: true, price: 30 })]);
    expect(html).toContain("Почти — нужно ⭐30");
  });

  it("never uses timers or scarcity wording", () => {
    const html = render([
      item({ state: "affordable" }),
      item({ code: "bim", state: "locked", unlocked: false, price: 100 }),
    ]).toLowerCase();
    for (const word of ["осталось", "успей", "таймер", "истек", "только сегодня", "спешите"]) {
      expect(html).not.toContain(word);
    }
  });

  it("disables the control for the mascot currently being changed", () => {
    const html = renderToStaticMarkup(
      createElement(Collection, {
        mascots: [item({ state: "affordable" })],
        balance: 12,
        busyCode: "tisha",
        onPurchase: () => {},
        onActivate: () => {},
      }),
    );
    expect(html).toContain("disabled");
    expect(html).toContain("Открываем…");
  });
});
