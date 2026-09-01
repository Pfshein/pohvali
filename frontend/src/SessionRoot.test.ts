import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { BootstrapScreen } from "./SessionRoot";
import { completeOnboarding, type OnboardingStorage } from "./lib/onboarding";

function markup(phase: "loading" | "session-error" | "storage-error"): string {
  return renderToStaticMarkup(createElement(BootstrapScreen, { phase, onRetry: () => {} }));
}

describe("bootstrap screens", () => {
  it("activates and persists the onboarding mascot", async () => {
    const events: string[] = [];
    const storage: OnboardingStorage = {
      get: async () => null,
      set: async (value) => {
        events.push(`stored:${value}`);
      },
    };

    await completeOnboarding(storage, "pol", async (code) => {
      events.push(`activated:${code}`);
    });

    expect(events).toEqual(["activated:pol", "stored:pol"]);
  });

  it("shows a calm loading screen", () => {
    expect(markup("loading")).toContain("Открываем тихое место");
  });

  it("offers retry when the session fails", () => {
    const html = markup("session-error");
    expect(html).toContain("Не получилось открыть приложение");
    expect(html).toContain("Попробовать снова");
  });

  it("explains on-device storage failure with its own copy and retry", () => {
    const html = markup("storage-error");
    expect(html).toContain("на этом устройстве");
    expect(html).toContain("Попробовать снова");
    expect(html).not.toContain("Не получилось открыть приложение");
  });
});
