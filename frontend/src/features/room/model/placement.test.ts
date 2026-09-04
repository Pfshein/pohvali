import { describe, expect, it } from "vitest";

import { dragPointToItemPosition } from "./placement";

describe("room drag projection", () => {
  it("preserves the point where the item was grabbed", () => {
    const position = dragPointToItemPosition(
      { x: 0.7, y: 0.8 },
      { x: 0.1, y: 0.05 },
      "floor",
    );

    expect(position).toEqual({ x: 0.6, y: 0.75 });
  });
});
