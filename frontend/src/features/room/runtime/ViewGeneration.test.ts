import { describe, expect, it } from "vitest";

import { ViewGeneration } from "./ViewGeneration";

describe("ViewGeneration", () => {
  it("invalidates stale async work when an id changes template", () => {
    const generations = new ViewGeneration();
    const oldToken = generations.begin("active-mascot", "mascot.ava");
    const newToken = generations.begin("active-mascot", "mascot.mira");

    expect(generations.isCurrent("active-mascot", oldToken)).toBe(false);
    expect(generations.isCurrent("active-mascot", newToken)).toBe(true);
  });

  it("invalidates pending work when an id is removed and re-added", () => {
    const generations = new ViewGeneration();
    const removedToken = generations.begin("chair", "chair.basic");
    generations.cancel("chair");
    const readdedToken = generations.begin("chair", "chair.basic");

    expect(generations.isCurrent("chair", removedToken)).toBe(false);
    expect(generations.isCurrent("chair", readdedToken)).toBe(true);
  });
});
