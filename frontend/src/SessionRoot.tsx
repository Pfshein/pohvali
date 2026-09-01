import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { App } from "./App";
import { Onboarding } from "./components/Onboarding";
import { STARTER_MASCOTS } from "./lib/mascots";
import { loadCalendar } from "./lib/calendar";
import { createAppBootstrap, type AppPhase } from "./lib/bootstrap";
import { loadOrCreateEncryptionKey, telegramKeyStorage } from "./lib/encryption-key";
import {
  completeOnboarding,
  loadOnboarding,
  saveOnboarding,
  telegramOnboardingStorage,
} from "./lib/onboarding";
import { activateMascot, loadCollection, purchaseMascot } from "./lib/mascots-api";
import { deleteAccountData } from "./lib/account";
import {
  enteredFromReminder,
  loadReminderOfferAnswered,
  markReminderOfferAnswered,
  telegramReminderOfferStorage,
} from "./lib/reminder-offer";
import {
  loadReminderSettings,
  setRemindersEnabled,
  type ReminderControls,
} from "./lib/reminders-api";
import { loadDay, savePraise } from "./lib/praise-api";
import { createRecoveryPhrase, restoreEncryptionKey } from "./lib/recovery-phrase";
import { openSession } from "./lib/session";
import type { TelegramClient } from "./lib/telegram";

interface SessionRootProps {
  client: TelegramClient;
}

function OnboardingGate({
  children,
  activateStarter,
}: {
  children: (mascotCode: string) => ReactNode;
  activateStarter: (code: string) => Promise<void>;
}) {
  const [status, setStatus] = useState<"unknown" | "needed" | "done">("unknown");
  const [step, setStep] = useState(0);
  const [mascot, setMascot] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const storage = useMemo(() => telegramOnboardingStorage(), []);

  useEffect(() => {
    void loadOnboarding(storage).then((state) => {
      setMascot(state.mascot);
      setStatus(state.completed ? "done" : "needed");
    });
  }, [storage]);

  if (status === "unknown") return null;
  if (status === "done" && mascot) return <>{children(mascot)}</>;

  return (
    <Onboarding
      step={step}
      mascots={STARTER_MASCOTS}
      selectedMascot={mascot}
      busy={saving}
      error={error}
      onSelectMascot={setMascot}
      onNext={() => setStep(1)}
      onFinish={() => {
        if (!mascot || saving) return;
        setSaving(true);
        setError("");
        void completeOnboarding(storage, mascot, activateStarter)
          .then(() => setStatus("done"))
          .catch(() => setError("Не получилось сохранить выбор. Можно попробовать ещё раз."))
          .finally(() => setSaving(false));
      }}
    />
  );
}

export function BootstrapScreen({
  phase,
  onRetry,
}: {
  phase: Exclude<AppPhase, "ready">;
  onRetry: () => void;
}) {
  return (
    <main className="session-screen">
      <section className="session-card" aria-live="polite">
        <span className="session-card__star" aria-hidden="true">★</span>
        {phase === "loading" && (
          <>
            <p className="eyebrow">Ещё мгновение</p>
            <h1>Открываем тихое место…</h1>
          </>
        )}
        {phase === "session-error" && (
          <>
            <p className="eyebrow">Связь прервалась</p>
            <h1>Не получилось открыть приложение</h1>
            <p>Можно спокойно попробовать ещё раз.</p>
            <button className="primary-button" onClick={onRetry}>
              Попробовать снова
            </button>
          </>
        )}
        {phase === "storage-error" && (
          <>
            <p className="eyebrow">Хранилище на паузе</p>
            <h1>Не удалось подготовить ключ на этом устройстве</h1>
            <p>Ключ шифрования хранится только здесь. Попробуем ещё раз?</p>
            <button className="primary-button" onClick={onRetry}>
              Попробовать снова
            </button>
          </>
        )}
      </section>
    </main>
  );
}

export function SessionRoot({ client }: SessionRootProps) {
  const [phase, setPhase] = useState<AppPhase>("loading");
  const [key, setKey] = useState<CryptoKey | null>(null);
  const [reminderOfferVisible, setReminderOfferVisible] = useState(false);
  const started = useRef(false);
  const keyStorage = useMemo(() => telegramKeyStorage(), []);
  const onboardingStorage = useMemo(() => telegramOnboardingStorage(), []);
  const reminderOfferStorage = useMemo(() => telegramReminderOfferStorage(), []);
  const mascotCollection = useMemo(
    () => ({
      load: () => loadCollection(client),
      purchase: (code: string) => purchaseMascot(client, code),
      activate: async (code: string) => {
        await activateMascot(client, code);
        await saveOnboarding(onboardingStorage, code);
      },
    }),
    [client, onboardingStorage],
  );
  const calendarLoader = useMemo(
    () => (from: string, to: string) => loadCalendar(client, from, to),
    [client],
  );
  const reminderControls = useMemo<ReminderControls>(
    () => ({
      load: () => loadReminderSettings(client),
      setEnabled: (enabled: boolean) => setRemindersEnabled(client, enabled),
    }),
    [client],
  );
  const reminderOffer = useMemo(() => {
    if (!reminderOfferVisible) return undefined;
    return {
      onAnswer: async (accepted: boolean) => {
        // The answer itself must stick even if the server sync hiccups; the
        // settings switch keeps showing and fixing the live server state.
        try {
          await setRemindersEnabled(client, accepted);
        } catch {
          // Best-effort sync: never re-ask because of a network error.
        }
        await markReminderOfferAnswered(reminderOfferStorage);
        setReminderOfferVisible(false);
      },
    };
  }, [client, reminderOfferStorage, reminderOfferVisible]);

  useEffect(() => {
    let active = true;
    void loadReminderOfferAnswered(reminderOfferStorage).then((answered) => {
      if (!active) return;
      const fromReminder = enteredFromReminder(window.location.search);
      setReminderOfferVisible(!answered && !fromReminder);
    });
    return () => {
      active = false;
    };
  }, [reminderOfferStorage]);
  const bootstrap = useMemo(
    () =>
      createAppBootstrap(
        {
          openSession: () => openSession(client),
          ensureKey: async () => {
            setKey(await loadOrCreateEncryptionKey(keyStorage));
          },
        },
        setPhase,
      ),
    [client, keyStorage],
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void bootstrap.connect();
  }, [bootstrap]);

  if (phase === "ready") {
    return (
      <OnboardingGate activateStarter={(code) => activateMascot(client, code)}>
        {(mascotCode) => <App
          firstName={client.getFirstName()}
          mascotCode={mascotCode}
          onSubmitPraise={key ? (text) => savePraise(client, key, text) : undefined}
          onExportRecoveryPhrase={key ? () => createRecoveryPhrase(key) : undefined}
          onImportRecoveryPhrase={key
            ? async (phrase) => {
                setKey(await restoreEncryptionKey(keyStorage, phrase));
              }
            : undefined}
          onDeleteAccount={() => deleteAccountData(client)}
          mascotCollection={mascotCollection}
          reminderOffer={reminderOffer}
          reminderControls={reminderControls}
          onLoadCalendar={calendarLoader}
          onLoadDay={key ? (date) => loadDay(client, key, date) : undefined}
        />}
      </OnboardingGate>
    );
  }

  return <BootstrapScreen phase={phase} onRetry={() => void bootstrap.connect()} />;
}
