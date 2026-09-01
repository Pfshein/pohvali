import type { Mascot } from "../lib/mascots";

interface OnboardingProps {
  step: number;
  mascots: readonly Mascot[];
  selectedMascot: string | null;
  onSelectMascot: (code: string) => void;
  onNext: () => void;
  onFinish: () => void;
}

export function Onboarding({
  step,
  mascots,
  selectedMascot,
  onSelectMascot,
  onNext,
  onFinish,
}: OnboardingProps) {
  return (
    <main className="session-screen">
      <section className="session-card" aria-live="polite">
        {step === 0 ? (
          <>
            <span className="session-card__star" aria-hidden="true">★</span>
            <p className="eyebrow">Тихое место</p>
            <h1>Раз в день — заметить, за что можно себя похвалить</h1>
            <p>
              Без давления и оценок. Пара секунд для себя, когда захочется. Текст шифруется
              на этом устройстве.
            </p>
            <button className="primary-button primary-button--wide" onClick={onNext}>
              Дальше
            </button>
          </>
        ) : (
          <>
            <p className="eyebrow">Последний шаг</p>
            <h1>Выбери спутника</h1>
            <p>Он будет рядом. Позже можно будет открыть и других.</p>
            <ul className="mascot-picker">
              {mascots.map((mascot) => (
                <li key={mascot.code}>
                  <button
                    className={
                      selectedMascot === mascot.code
                        ? "mascot-option mascot-option--selected"
                        : "mascot-option"
                    }
                    aria-pressed={selectedMascot === mascot.code}
                    onClick={() => onSelectMascot(mascot.code)}
                  >
                    <img src={mascot.assetPath} alt="" aria-hidden="true" />
                    <span className="mascot-option__copy">
                      <strong>{mascot.name}</strong>
                      <span>{mascot.blurb}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <button
              className="primary-button primary-button--wide"
              disabled={selectedMascot === null}
              onClick={onFinish}
            >
              Начать
            </button>
          </>
        )}
      </section>
    </main>
  );
}
