import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

import { renderPolicyPage } from "./scripts/render-privacy-page.ts";

/**
 * Publishes /privacy.html from the same source the in-app policy renders from,
 * so the page documented in docs/deploy.md cannot drift from what users read
 * inside the app. Served in dev and emitted into the build.
 */
function privacyPage(): Plugin {
  return {
    name: "pohvala-privacy-page",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.split("?")[0] !== "/privacy.html") {
          next();
          return;
        }
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        res.end(renderPolicyPage());
      });
    },
    generateBundle() {
      this.emitFile({
        type: "asset",
        fileName: "privacy.html",
        source: renderPolicyPage(),
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), privacyPage()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost",
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
