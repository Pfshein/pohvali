import { describe, expect, it } from "vitest";

import { RoomDragSession } from "./RoomDragSession";

describe("RoomDragSession", () => {
  it("keeps ownership with the first pointer until it finishes", () => {
    const drag = new RoomDragSession();

    expect(drag.start("chair", 1, { x: 0.5, y: 0.7 }, { x: 0.55, y: 0.75 })).toBe(true);
    expect(drag.start("mascot", 2, { x: 0.4, y: 0.8 }, { x: 0.4, y: 0.8 })).toBe(false);
    expect(drag.move(2, { x: 0.8, y: 0.8 }, "floor")).toBeNull();
    expect(drag.finish(2)).toBeNull();
    expect(drag.finish(1)).toEqual({ id: "chair", position: { x: 0.5, y: 0.7 } });
  });

  it("returns the committed origin so cancellation can restore the view", () => {
    const drag = new RoomDragSession();
    drag.start("chair", 7, { x: 0.5, y: 0.7 }, { x: 0.5, y: 0.7 });
    drag.move(7, { x: 0.8, y: 0.85 }, "floor");

    expect(drag.cancel(7)).toEqual({ id: "chair", position: { x: 0.5, y: 0.7 } });
    expect(drag.finish(7)).toBeNull();
  });
});
