import { describe, expect, it } from "vitest";

import { resolveRoomMascot } from "./roomMascot";
import type { MascotCollection } from "../../../lib/mascots-api";

function collection(activeMascot: string | null, codes: readonly string[]): MascotCollection {
  return {
    balance: 2,
    activeMascot,
    mascots: codes.map((code, index) => ({
      code,
      name: `Спутник ${index}`,
      blurb: "",
      assetPath: `/assets/mascots/${code}.png`,
      starter: false,
      price: null,
      state: "owned",
      unlocked: true,
      active: code === activeMascot,
    })),
  };
}

describe("resolveRoomMascot", () => {
  it("uses the actual collection entry for an admin mascot the local list lacks", () => {
    const mascot = resolveRoomMascot(collection("ufo-77", ["ava", "ufo-77"]), "ufo-77");

    expect(mascot).toEqual({
      code: "ufo-77",
      name: "Спутник 1",
      assetPath: "/assets/mascots/ufo-77.png",
    });
  });

  it("prefers the freshly activated code over a stale collection answer", () => {
    // activate() updates the local code first; the collection still reports the
    // previous mascot until its reload lands (and may never, if that fails).
    const mascot = resolveRoomMascot(collection("ava", ["ava", "ufo-77"]), "ufo-77");

    expect(mascot).toEqual({
      code: "ufo-77",
      name: "Спутник 1",
      assetPath: "/assets/mascots/ufo-77.png",
    });
  });

  it("uses the collection answer when no local code is known yet", () => {
    const mascot = resolveRoomMascot(collection("ufo-77", ["ava", "ufo-77"]), null);

    expect(mascot.code).toBe("ufo-77");
  });

  it("falls back to the local starter list when the collection has not loaded", () => {
    const mascot = resolveRoomMascot(null, "mira");

    expect(mascot.code).toBe("mira");
    expect(mascot.name).toBe("Кошка Мира");
    expect(mascot.assetPath).toBe("/assets/mascots/mira.png");
  });

  it("falls back when the active code is missing from the response", () => {
    const mascot = resolveRoomMascot(collection(null, ["ava"]), "pol");

    expect(mascot.code).toBe("pol");
    expect(mascot.assetPath).toBe("/assets/mascots/pol.png");
  });
});
