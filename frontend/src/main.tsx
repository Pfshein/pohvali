import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/nunito/500.css";
import "@fontsource/nunito/600.css";
import "@fontsource/nunito/700.css";
import "@fontsource/nunito/800.css";

import { SessionRoot } from "./SessionRoot";
import "./styles.css";
import { createTelegramClient } from "./lib/telegram";

async function start() {
  const mock = import.meta.env.VITE_TELEGRAM_MODE === "mock"
    ? await import("./lib/dev-telegram")
    : undefined;
  const telegramClient = createTelegramClient({
    mode: mock ? "mock" : "telegram",
    webApp: mock ? undefined : window.Telegram?.WebApp,
    mock: mock ? {
      createInitData: mock.createDevInitData,
      firstName: mock.getDevFirstName(),
    } : undefined,
  });
  telegramClient.initialize();

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <SessionRoot client={telegramClient} />
    </StrictMode>,
  );
}

void start();
