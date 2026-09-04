import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RoomHome, type RoomHomeProps } from "./RoomHome";
import { createRoomCatalog, type RoomMascotAsset } from "../catalog/roomCatalog";
import { createStarterRoom } from "../catalog/starterRoom";
import type { RoomRenderer } from "../runtime/RoomRuntime";

const mira: RoomMascotAsset = {
  code: "mira",
  name: "Кошка Мира",
  assetPath: "/assets/mascots/mira.png",
};

const fakeRenderer: RoomRenderer = {
  mount: async () => undefined,
  update: () => undefined,
  resize: () => undefined,
  setEditing: () => undefined,
  destroy: () => undefined,
};

function renderHome(overrides: Partial<RoomHomeProps> = {}): string {
  const catalog = createRoomCatalog([mira]);
  const props: RoomHomeProps = {
    mascot: mira,
    praisedDayCount: 0,
    room: createStarterRoom(mira, catalog),
    editing: false,
    onRoomChange: () => undefined,
    onEditingChange: () => undefined,
    onOpenOverlay: () => undefined,
    createRenderer: () => fakeRenderer,
    ...overrides,
  };
  vi.stubGlobal("window", { Telegram: undefined });
  return renderToStaticMarkup(createElement(RoomHome, props));
}

describe("RoomHome first viewport", () => {
  it("renders the accepted copy with five accessible controls and no canvas element", () => {
    const markup = renderHome();

    expect(markup).toContain("За что ты хочешь похвалить себя сегодня?");
    expect(markup).toContain("Сегодня можно начать");
    expect(markup).toContain(">Обустроить<");
    expect(markup).toContain('aria-label="Открыть настройки"');
    expect(markup).toContain('aria-label="Открыть календарь"');
    expect(markup).toContain('aria-label="Похвалить себя"');
    expect(markup).toContain('aria-label="Открыть профиль"');
    expect(markup).toContain('class="room-canvas"');
    expect(markup).not.toContain("<canvas");
    expect(markup).not.toContain("подряд");
  });

  it("word the progress message by count without streak language", () => {
    expect(renderHome({ praisedDayCount: 1 })).toContain("1 день заботы о себе");
    expect(renderHome({ praisedDayCount: 2 })).toContain("2 дня заботы о себе");
    expect(renderHome({ praisedDayCount: 4 })).toContain("4 дня заботы о себе");
    expect(renderHome({ praisedDayCount: 7 })).toContain("7 дней заботы о себе");

    const markup = renderHome({ praisedDayCount: 3 });
    expect(markup).toContain('aria-label="В этом месяце: 3 дня заботы о себе"');
  });

  it("toggles the furnish control and keeps the calm tagline", () => {
    const editing = renderHome({ editing: true });

    expect(editing).toContain(">Готово<");
    expect(editing).toContain('aria-pressed="true"');
    expect(renderHome({ editing: false })).toContain('aria-pressed="false"');
    expect(editing).toContain("Твой уют начинается");
    expect(editing).toContain("с малого шага 🌿");
  });

  it("describes the meaningful scene next to the hidden canvas", () => {
    const markup = renderHome();

    expect(markup).toContain('aria-hidden="true"'); // canvas host
    expect(markup).toContain("Кошка Мира в уютном кресле"); // scene description
  });
});
