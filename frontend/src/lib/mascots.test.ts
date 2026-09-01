/// <reference types="node" />

import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { findMascot, MASCOTS, STARTER_MASCOTS, unlockedMascotMessage } from "./mascots";

describe("mascot catalog", () => {
  it("contains six unique stable codes and three starter choices", () => {
    expect(MASCOTS).toHaveLength(6);
    expect(new Set(MASCOTS.map((mascot) => mascot.code)).size).toBe(MASCOTS.length);
    expect(STARTER_MASCOTS.map((mascot) => mascot.code)).toEqual(["ava", "pol", "mira"]);
  });

  it("points every catalog entry to an existing public asset", () => {
    for (const mascot of MASCOTS) {
      const asset = fileURLToPath(new URL(`../../public${mascot.assetPath}`, import.meta.url));
      expect(existsSync(asset), `${mascot.code}: ${asset}`).toBe(true);
    }
  });

  it("falls back to the first starter for an unknown stored code", () => {
    expect(findMascot("old-code").code).toBe("ava");
  });

  it("turns newly unlocked codes into a calm user-facing message", () => {
    expect(unlockedMascotMessage(["tisha"])).toBe(
      "Открылся новый спутник — Капибара Тиша",
    );
    expect(unlockedMascotMessage(["unknown"])).toBeNull();
  });
});
