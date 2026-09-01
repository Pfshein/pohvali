import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { RecoveryAccess } from "./RecoveryAccess";

describe("recovery access", () => {
  it("does not export or render a phrase before the user opens it", () => {
    const exportPhrase = vi.fn(async () => "pohvala-v1.secret.checksum");

    const markup = renderToStaticMarkup(
      createElement(RecoveryAccess, {
        onExport: exportPhrase,
        onImport: vi.fn(async () => {}),
      }),
    );

    expect(markup).toContain("Доступ к записям");
    expect(markup).not.toContain("pohvala-v1.secret.checksum");
    expect(exportPhrase).not.toHaveBeenCalled();
  });
});
