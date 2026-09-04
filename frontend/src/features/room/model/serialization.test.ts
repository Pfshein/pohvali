import { describe, expect, it } from "vitest";

import { parseRoomState, serializeRoomState, type RoomTemplateLookup } from "./serialization";
import type { RoomItem, RoomState } from "./room";

const templates: RoomTemplateLookup = {
  has: (templateId) => templateId === "chair.basic.back" || templateId === "mascot.mira",
};

function validItem(): RoomItem {
  return {
    id: "seat-back",
    templateId: "chair.basic.back",
    position: { x: 0.5, y: 0.73 },
    scale: 1,
    rotation: 0,
    layer: "furniture",
    zIndex: 0,
    zoneId: "fixed",
    locked: true,
  };
}

function validState(): RoomState {
  return { schemaVersion: 1, items: [validItem()] };
}

describe("room state serialization", () => {
  it("round-trips a valid schemaVersion 1 room", () => {
    const state = validState();

    const parsed = parseRoomState(serializeRoomState(state), templates);

    expect(parsed).toEqual({ ok: true, state });
  });

  it("rejects malformed JSON and non-object payloads", () => {
    expect(parseRoomState("not-json", templates)).toEqual({ ok: false, error: "malformed" });
    expect(parseRoomState("42", templates)).toEqual({ ok: false, error: "malformed" });
    expect(parseRoomState("null", templates)).toEqual({ ok: false, error: "malformed" });
  });

  it("rejects unknown schema versions", () => {
    const raw = JSON.stringify({ schemaVersion: 2, items: [] });
    expect(parseRoomState(raw, templates)).toEqual({ ok: false, error: "unsupported-version" });
  });

  it("rejects non-finite and out-of-range coordinates", () => {
    for (const position of [
      { x: Number.NaN, y: 0.5 },
      { x: Number.POSITIVE_INFINITY, y: 0.5 },
      { x: -0.1, y: 0.5 },
      { x: 0.5, y: 1.2 },
    ]) {
      const raw = JSON.stringify({ schemaVersion: 1, items: [{ ...validItem(), position }] });
      expect(parseRoomState(raw, templates)).toEqual({ ok: false, error: "invalid-item" });
    }
  });

  it("rejects duplicate ids", () => {
    const raw = JSON.stringify({
      schemaVersion: 1,
      items: [validItem(), { ...validItem(), templateId: "mascot.mira" }],
    });

    expect(parseRoomState(raw, templates)).toEqual({ ok: false, error: "duplicate-id" });
  });

  it("rejects template ids absent from the supplied catalog", () => {
    const raw = JSON.stringify({
      schemaVersion: 1,
      items: [{ ...validItem(), templateId: "chair.basic.front" }],
    });

    expect(parseRoomState(raw, templates)).toEqual({ ok: false, error: "unknown-template" });
  });

  it("rejects invalid layers, zones and non-integer z-index", () => {
    for (const overrides of [
      { layer: "ceiling" },
      { zoneId: "roof" },
      { zIndex: 1.5 },
      { zIndex: 500 },
      { zIndex: -500 },
      { scale: 0 },
      { scale: Number.NaN },
    ]) {
      const raw = JSON.stringify({
        schemaVersion: 1,
        items: [{ ...validItem(), ...overrides }],
      });
      expect(parseRoomState(raw, templates)).toEqual({ ok: false, error: "invalid-item" });
    }
  });
});
