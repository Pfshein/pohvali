import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { PrivacyPanel } from "./PrivacyPanel";

describe("privacy panel", () => {
  it("stays closed and does not call deletion before the user opens it", () => {
    const deleteAccount = vi.fn(async () => {});

    const markup = renderToStaticMarkup(
      createElement(PrivacyPanel, { onDeleteAccount: deleteAccount }),
    );

    expect(markup).toContain("Приватность и данные");
    expect(markup).not.toContain("Удалить мои данные");
    expect(deleteAccount).not.toHaveBeenCalled();
  });

  it("explains what is stored and links the full policy once opened", () => {
    const markup = renderToStaticMarkup(
      createElement(PrivacyPanel, {
        onDeleteAccount: vi.fn(async () => {}),
        initialStep: "confirm",
      }),
    );

    expect(markup).toContain("шифруются на устройстве");
    expect(markup).toContain('href="/privacy.html"');
    expect(markup).toContain("Удалить мои данные");
    expect(markup).toContain("нельзя отменить");
    expect(markup).toContain("Оставить");
  });

  it("shows a calm completion state without pressure wording", () => {
    const markup = renderToStaticMarkup(
      createElement(PrivacyPanel, {
        onDeleteAccount: vi.fn(async () => {}),
        initialStep: "done",
      }),
    );

    expect(markup).toContain("данные удалены с сервера");
    expect(markup).toContain("Начать заново");
    expect(markup).not.toContain("потеря");
    expect(markup).not.toContain("пропуст");
  });
});
