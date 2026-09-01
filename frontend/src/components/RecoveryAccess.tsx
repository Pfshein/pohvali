import { useState } from "react";

interface RecoveryAccessProps {
  onExport: () => Promise<string>;
  onImport: (phrase: string) => Promise<void>;
}

type RecoveryView = "menu" | "export" | "import";

export function RecoveryAccess({ onExport, onImport }: RecoveryAccessProps) {
  const [isOpen, setOpen] = useState(false);
  const [view, setView] = useState<RecoveryView>("menu");
  const [phrase, setPhrase] = useState("");
  const [input, setInput] = useState("");
  const [message, setMessage] = useState("");
  const [isWorking, setWorking] = useState(false);

  function close() {
    setOpen(false);
    setView("menu");
    setPhrase("");
    setInput("");
    setMessage("");
    setWorking(false);
  }

  async function showPhrase() {
    if (isWorking) return;
    setWorking(true);
    setMessage("");
    try {
      setPhrase(await onExport());
      setView("export");
    } catch {
      setMessage("Не удалось подготовить фразу. Можно попробовать ещё раз.");
    } finally {
      setWorking(false);
    }
  }

  async function copyPhrase() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard is unavailable");
      await navigator.clipboard.writeText(phrase);
      setMessage("Фраза скопирована");
    } catch {
      setMessage("Можно выделить фразу и скопировать её вручную.");
    }
  }

  async function importPhrase() {
    if (!input.trim() || isWorking) return;
    setWorking(true);
    setMessage("");
    try {
      await onImport(input);
      setInput("");
      setMessage("Ключ сохранён на этом устройстве.");
    } catch {
      setMessage("Не удалось восстановить ключ. Проверь фразу и попробуй ещё раз.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <>
      <button className="recovery-trigger" onClick={() => setOpen(true)}>
        Доступ к записям
      </button>

      {isOpen && (
        <div className="scrim" role="presentation" onMouseDown={close}>
          <section
            className="composer recovery-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="recovery-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="composer__handle" />
            <button className="composer__close" onClick={close} aria-label="Закрыть">×</button>

            <p className="eyebrow">Только на твоих устройствах</p>
            <h2 id="recovery-title">Доступ к записям</h2>

            {view === "menu" && (
              <>
                <p className="recovery-dialog__copy">
                  Фраза восстановления поможет открыть записи после смены устройства. Мы не
                  отправляем её на наш сервер и не сможем подсказать заново.
                </p>
                <div className="recovery-dialog__actions">
                  <button className="primary-button primary-button--wide" onClick={() => void showPhrase()}>
                    {isWorking ? "Готовим…" : "Показать мою фразу"}
                  </button>
                  <button className="secondary-button" onClick={() => { setView("import"); setMessage(""); }}>
                    Ввести сохранённую фразу
                  </button>
                </div>
              </>
            )}

            {view === "export" && (
              <>
                <p className="recovery-dialog__copy">
                  Сохрани её в надёжном месте. Любой, кто увидит фразу, сможет прочитать записи.
                </p>
                <textarea
                  className="recovery-phrase"
                  aria-label="Фраза восстановления"
                  readOnly
                  value={phrase}
                  onFocus={(event) => event.currentTarget.select()}
                />
                <button className="primary-button primary-button--wide" onClick={() => void copyPhrase()}>
                  Скопировать фразу
                </button>
              </>
            )}

            {view === "import" && (
              <>
                <p className="recovery-dialog__copy">
                  Вставь фразу целиком. Она заменит ключ на этом устройстве.
                </p>
                <textarea
                  className="recovery-phrase recovery-phrase--input"
                  aria-label="Введите фразу восстановления"
                  autoComplete="off"
                  maxLength={256}
                  spellCheck={false}
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="pohvala-v1.…"
                />
                <button
                  className="primary-button primary-button--wide"
                  disabled={!input.trim() || isWorking}
                  onClick={() => void importPhrase()}
                >
                  {isWorking ? "Проверяем…" : "Восстановить ключ"}
                </button>
              </>
            )}

            {message && <p className="recovery-dialog__message" role="status">{message}</p>}
          </section>
        </div>
      )}
    </>
  );
}
