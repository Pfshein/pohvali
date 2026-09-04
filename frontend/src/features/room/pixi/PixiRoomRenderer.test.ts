import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Pixi needs a real GPU context, so the library is stubbed at its module
 * boundary. What is under test is our own failure handling: a renderer that
 * cannot start must not strand the Application object it already created.
 */
const pixi = vi.hoisted(() => ({
  appDestroy: vi.fn(),
  appInit: vi.fn(() => Promise.reject(new Error("WebGL unavailable"))),
}));

vi.mock("pixi.js", () => ({
  Application: class {
    canvas = { style: {} };
    stage = {};
    renderer = { width: 0, height: 0 };
    init = pixi.appInit;
    destroy = pixi.appDestroy;
  },
  Assets: { load: vi.fn() },
  Container: class {},
  FillGradient: class {},
  Graphics: class {},
  Sprite: class {},
  Texture: class {},
}));

const { PixiRoomRenderer } = await import("./PixiRoomRenderer");
const { createRoomCatalog } = await import("../catalog/roomCatalog");
const { createStarterRoom } = await import("../catalog/starterRoom");

const mira = { code: "mira", name: "Кошка Мира", assetPath: "/assets/mascots/mira.png" };

function host(): HTMLElement {
  return { clientWidth: 390, clientHeight: 844, appendChild: vi.fn() } as unknown as HTMLElement;
}

describe("PixiRoomRenderer failure handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("window", { devicePixelRatio: 2 });
  });

  it("releases the application it created when Pixi cannot initialise", async () => {
    const catalog = createRoomCatalog([mira]);
    const renderer = new PixiRoomRenderer({ catalog, onItemMove: () => undefined });

    await expect(renderer.mount(host(), createStarterRoom(mira, catalog)))
      .rejects.toThrow("WebGL unavailable");

    expect(pixi.appDestroy).toHaveBeenCalledTimes(1);
  });

  it("stays safe to destroy after a failed mount", async () => {
    const catalog = createRoomCatalog([mira]);
    const renderer = new PixiRoomRenderer({ catalog, onItemMove: () => undefined });

    await expect(renderer.mount(host(), createStarterRoom(mira, catalog))).rejects.toThrow();

    expect(() => renderer.destroy()).not.toThrow();
    // The failed application was already released; destroy must not repeat it.
    expect(pixi.appDestroy).toHaveBeenCalledTimes(1);
  });
});
