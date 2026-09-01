import { useEffect, useState } from "react";

import type { ReminderControls, ReminderSettings } from "../lib/reminders-api";

interface ReminderSettingsProps {
  controls: ReminderControls;
  initialSettings?: ReminderSettings;
}

type Phase = "loading" | "ready" | "error";

export function ReminderSettings({ controls, initialSettings }: ReminderSettingsProps) {
  const [phase, setPhase] = useState<Phase>(initialSettings ? "ready" : "loading");
  const [settings, setSettings] = useState<ReminderSettings | null>(initialSettings ?? null);
  const [isBusy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (initialSettings) return;
    let active = true;
    void controls.load()
      .then((loaded) => {
        if (active) {
          setSettings(loaded);
          setPhase("ready");
        }
      })
      .catch(() => {
        if (active) setPhase("error");
      });
    return () => {
      active = false;
    };
  }, [controls, initialSettings]);

  async function toggle() {
    if (settings === null || isBusy) return;
    setBusy(true);
    setMessage("");
    try {
      setSettings(await controls.setEnabled(!settings.enabled));
    } catch {
      setMessage("Не получилось изменить. Можно попробовать ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="reminder-settings" aria-labelledby="reminder-settings-title">
      <div className="reminder-settings__info">
        <h2 id="reminder-settings-title">Напоминания</h2>
        <p className="reminder-settings__copy">
          Одно тихое сообщение около 22:00, если сегодня ещё не было похвалы.
        </p>
        {phase === "ready" && settings !== null && !settings.dmAvailable && (
          <p className="reminder-settings__hint">
            Чтобы напоминания приходили, достаточно один раз открыть чат с ботом.
          </p>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={settings?.enabled ?? false}
        aria-label="Напоминания"
        className="reminder-switch"
        disabled={phase !== "ready" || isBusy}
        onClick={() => void toggle()}
      >
        <span aria-hidden="true">
          {phase === "ready" && settings !== null
            ? settings.enabled ? "Включены" : "Выключены"
            : "…"}
        </span>
      </button>
      {phase === "error" && (
        <p className="inline-note" role="status">
          Не удалось открыть настройки напоминаний.
        </p>
      )}
      {message && <p className="inline-note" role="status">{message}</p>}
    </section>
  );
}
