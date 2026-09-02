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

  it("explains what is stored and offers the full policy once opened", () => {
    const markup = renderToStaticMarkup(
      createElement(PrivacyPanel, {
        onDeleteAccount: vi.fn(async () => {}),
        initialStep: "confirm",
      }),
    );

    expect(markup).toContain("шифруются на устройстве");
    expect(markup).toContain("Политика конфиденциальности");
    expect(markup).toContain("Удалить мои данные");
    expect(markup).toContain("нельзя отменить");
    expect(markup).toContain("Оставить");
  });

  it("keeps the reader in the app: the policy opens inline, not as a link out", () => {
    const markup = renderToStaticMarkup(
      createElement(PrivacyPanel, {
        onDeleteAccount: vi.fn(async () => {}),
        initialView: "policy",
      }),
    );

    // The whole policy is present in the dialog itself.
    expect(markup).toContain("Как работает шифрование");
    expect(markup).toContain("Что мы не храним");
    expect(markup).toContain("Резервные копии");
    expect(markup).toContain("Назад");

    // Nothing sends the user to an external page or a new browser tab.
    expect(markup).not.toContain("privacy.html");
    expect(markup).not.toContain("target=\"_blank\"");
    expect(markup).not.toContain("<a ");
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
