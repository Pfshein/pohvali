import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { STARTER_MASCOTS } from "../lib/mascots";
import { Onboarding } from "./Onboarding";

function render(overrides: Partial<Parameters<typeof Onboarding>[0]> = {}): string {
  return renderToStaticMarkup(
    createElement(Onboarding, {
      step: 0,
      mascots: STARTER_MASCOTS,
      selectedMascot: null,
      onSelectMascot: () => {},
      onNext: () => {},
      onFinish: () => {},
      ...overrides,
    }),
  );
}

describe("Onboarding", () => {
  it("uses at most two screens and puts the mascot pick last", () => {
    expect(STARTER_MASCOTS.length).toBeGreaterThan(0);

    const intro = render({ step: 0 });
    expect(intro).toContain("Дальше");
    expect(intro).not.toContain("Начать");

    const pick = render({ step: 1 });
    expect(pick).toContain("Выбери спутника");
    expect(pick).toContain("Начать");
    for (const mascot of STARTER_MASCOTS) {
      expect(pick).toContain(mascot.name);
    }
  });

  it("lets the person continue without any push permission gate", () => {
    const intro = render({ step: 0 }).toLowerCase();

    expect(intro).not.toContain("уведомл");
    expect(intro).not.toContain("push");
    expect(intro).not.toContain("разреши");
  });

  it("blocks finishing until a starter is chosen, then allows it", () => {
    expect(render({ step: 1, selectedMascot: null })).toContain("disabled");
    expect(render({ step: 1, selectedMascot: "ava" })).toContain('aria-pressed="true"');
  });
});
