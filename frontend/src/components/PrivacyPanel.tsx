import { useState } from "react";

import { nextDeletionStep, type DeletionStep } from "../lib/account";
import { PrivacyPolicy } from "./PrivacyPolicy";

type PanelView = "summary" | "policy";

interface PrivacyPanelProps {
  onDeleteAccount: () => Promise<void>;
  initialStep?: DeletionStep;
  initialView?: PanelView;
}

export function PrivacyPanel({
  onDeleteAccount,
  initialStep = "idle",
  initialView = "summary",
}: PrivacyPanelProps) {
  const [isOpen, setOpen] = useState(initialStep !== "idle" || initialView !== "summary");
  const [step, setStep] = useState<DeletionStep>(initialStep);
  const [view, setView] = useState<PanelView>(initialView);

  function close() {
    setOpen(false);
    setStep("idle");
    setView("summary");
  }

  async function confirmDeletion() {
    setStep((current) => nextDeletionStep(current, "confirm"));
    try {
      await onDeleteAccount();
      setStep((current) => nextDeletionStep(current, "succeeded"));
    } catch {
      setStep((current) => nextDeletionStep(current, "failed"));
    }
  }

  return (
    <>
      <button className="recovery-trigger" onClick={() => setOpen(true)}>
        Приватность и данные
      </button>

      {isOpen && (
        <div className="scrim" role="presentation" onMouseDown={close}>
          <section
            className="composer recovery-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="privacy-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="composer__handle" />
            <button className="composer__close" onClick={close} aria-label="Закрыть">×</button>

            {view === "policy" ? (
              <>
                <p className="eyebrow">Полный текст</p>
                <h2 id="privacy-title">Политика конфиденциальности</h2>

                <div className="policy-scroll" tabIndex={0}>
                  <PrivacyPolicy />
                </div>

                <div className="recovery-dialog__actions">
                  <button className="secondary-button" onClick={() => setView("summary")}>
                    Назад
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="eyebrow">Спокойно и прозрачно</p>
                <h2 id="privacy-title">Приватность и данные</h2>

                <p className="recovery-dialog__copy">
                  Записи шифруются на устройстве до отправки. На сервере хранится только
                  зашифрованный текст, твой числовой Telegram ID, часовой пояс, счётчики
                  звёзд и настройки напоминаний. Имя, фото и язык мы не получаем.
                </p>

                <div className="recovery-dialog__actions">
                  <button className="secondary-button" onClick={() => setView("policy")}>
                    Политика конфиденциальности
                  </button>
                </div>

                {step === "idle" && (
                  <>
                    <p className="recovery-dialog__copy">
                      Можно в любой момент удалить свои данные с сервера.
                    </p>
                    <div className="recovery-dialog__actions">
                      <button
                        className="secondary-button"
                        onClick={() => setStep((current) => nextDeletionStep(current, "request"))}
                      >
                        Удалить мои данные
                      </button>
                    </div>
                  </>
                )}

                {step === "confirm" && (
                  <>
                    <h3>Удалить мои данные?</h3>
                    <p className="recovery-dialog__copy">
                      Записи, звёзды и маскоты будут удалены с сервера. Это действие
                      нельзя отменить. Ключ шифрования останется на твоих устройствах.
                    </p>
                    <div className="recovery-dialog__actions">
                      <button
                        className="primary-button"
                        onClick={() => void confirmDeletion()}
                      >
                        Да, удалить
                      </button>
                      <button
                        className="secondary-button"
                        onClick={() => setStep((current) => nextDeletionStep(current, "cancel"))}
                      >
                        Оставить
                      </button>
                    </div>
                  </>
                )}

                {step === "working" && (
                  <p className="recovery-dialog__message" role="status">Удаляем данные…</p>
                )}

                {step === "done" && (
                  <>
                    <p className="recovery-dialog__copy">
                      Готово: данные удалены с сервера. Ключ шифрования остался на твоих
                      устройствах.
                    </p>
                    <button
                      className="primary-button primary-button--wide"
                      onClick={() => window.location.reload()}
                    >
                      Начать заново
                    </button>
                  </>
                )}

                {step === "error" && (
                  <>
                    <p className="recovery-dialog__message" role="status">
                      Не получилось удалить данные. Можно спокойно попробовать ещё раз.
                    </p>
                    <div className="recovery-dialog__actions">
                      <button
                        className="secondary-button"
                        onClick={() => setStep((current) => nextDeletionStep(current, "request"))}
                      >
                        Попробовать снова
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}
