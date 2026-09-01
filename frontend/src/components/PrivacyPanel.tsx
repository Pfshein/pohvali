import { useState } from "react";

import { nextDeletionStep, type DeletionStep } from "../lib/account";

interface PrivacyPanelProps {
  onDeleteAccount: () => Promise<void>;
  policyUrl?: string;
  initialStep?: DeletionStep;
}

export function PrivacyPanel({
  onDeleteAccount,
  policyUrl = "/privacy.html",
  initialStep = "idle",
}: PrivacyPanelProps) {
  const [isOpen, setOpen] = useState(initialStep !== "idle");
  const [step, setStep] = useState<DeletionStep>(initialStep);

  function close() {
    setOpen(false);
    setStep("idle");
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

            <p className="eyebrow">Спокойно и прозрачно</p>
            <h2 id="privacy-title">Приватность и данные</h2>

            <p className="recovery-dialog__copy">
              Записи шифруются на устройстве до отправки. На сервере хранится только
              зашифрованный текст, твой числовой Telegram ID, часовой пояс, счётчики
              звёзд и настройки напоминаний. Имя, фото и язык мы не получаем.
            </p>

            <div className="recovery-dialog__actions">
              <a
                className="secondary-button"
                href={policyUrl}
                target="_blank"
                rel="noreferrer"
              >
                Политика конфиденциальности
              </a>
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
          </section>
        </div>
      )}
    </>
  );
}
