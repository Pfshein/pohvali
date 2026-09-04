import { describe, expect, it } from "vitest";
import { loadUiMode, parseUiModePreference, saveUiMode } from "./ui-mode";

describe("UI mode preference", () => {
  it("defaults malformed and unknown data to classic", () => {
    expect(parseUiModePreference(null)).toBe("classic");
    expect(parseUiModePreference("not-json")).toBe("classic");
    expect(parseUiModePreference('{"schemaVersion":2,"mode":"room"}')).toBe("classic");
    expect(parseUiModePreference('{"schemaVersion":1,"mode":"other"}')).toBe("classic");
  });

  it("round-trips room without throwing when storage works", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => void values.set(key, value),
    };
    saveUiMode("room", storage);
    expect(loadUiMode(storage)).toBe("room");
  });

  it("keeps classic usable when storage throws", () => {
    const storage = {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("blocked"); },
    };
    expect(loadUiMode(storage)).toBe("classic");
    expect(() => saveUiMode("room", storage)).not.toThrow();
  });
});
