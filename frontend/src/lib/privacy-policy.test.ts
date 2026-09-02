import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PrivacyPolicy } from "../components/PrivacyPolicy";
import { renderPolicyPage } from "../../scripts/render-privacy-page";
import { PRIVACY_POLICY, policyMeta } from "./privacy-policy";

// Sections the PH-706 design requires the published policy to cover.
const REQUIRED_SECTIONS = [
  "Коротко",
  "Как работает шифрование",
  "Что мы храним",
  "Что мы не храним",
  "Telegram и границы доверия",
  "Напоминания",
  "Удаление данных",
  "Где находятся данные",
  "Резервные копии",
  "Изменения и контакт",
];

describe("privacy policy source", () => {
  it("covers every required section", () => {
    const headings = PRIVACY_POLICY.sections.map((section) => section.heading);

    expect(headings).toEqual(REQUIRED_SECTIONS);
  });

  it("states its version and revision date", () => {
    expect(policyMeta()).toContain("версия 1.0");
    expect(policyMeta()).toContain("редакция от 02.09.2026");
  });
});

describe("published /privacy.html", () => {
  const page = renderPolicyPage();

  it("is a self-contained document with no external resources", () => {
    expect(page.startsWith("<!doctype html>")).toBe(true);
    expect(page).toContain('<html lang="ru">');
    expect(page).toContain("<style>");
    // No script, and nothing fetched from another origin.
    expect(page).not.toContain("<script");
    expect(page).not.toContain("http://");
    expect(page).not.toContain("https://");
  });

  it("carries the whole policy", () => {
    for (const heading of REQUIRED_SECTIONS) {
      expect(page).toContain(heading);
    }
    expect(page).toContain(policyMeta());
    expect(page).toContain("<strong>на вашем устройстве</strong>");
  });
});

describe("policy shown in the app", () => {
  // The published page and the in-app view render from one source, so a change
  // to the policy cannot reach a user through one surface and not the other.
  it("matches the published page section for section", () => {
    const markup = renderToStaticMarkup(createElement(PrivacyPolicy));
    const page = renderPolicyPage();

    for (const heading of REQUIRED_SECTIONS) {
      expect(markup).toContain(heading);
      expect(page).toContain(heading);
    }
    expect(markup).toContain(policyMeta());
    expect(markup).toContain("<strong>на вашем устройстве</strong>");
  });
});
