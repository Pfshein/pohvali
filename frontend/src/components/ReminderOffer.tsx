import { useState } from "react";

interface ReminderOfferProps {
  onAnswer: (accepted: boolean) => Promise<void>;
}

type OfferPhase = "asking" | "working" | "answered" | "error";

export function ReminderOffer({ onAnswer }: ReminderOfferProps) {
  const [phase, setPhase] = useState<OfferPhase>("asking");

  async function answer(accepted: boolean) {
    if (phase === "working" || phase === "answered") return;
    setPhase("working");
    try {
      await onAnswer(accepted);
      setPhase("answered");
    } catch {
      setPhase("error");
    }
  }

  if (phase === "answered") return null;

  return (
    <section className="reminder-card" aria-labelledby="reminder-offer-title">
      <p className="eyebrow">Спокойная минутка</p>
      <h2 id="reminder-offer-title">Присылать тихое напоминание вечером?</h2>
      <p className="reminder-card__copy">
        Около 22:00 по твоему времени бот может написать одно короткое сообщение,
        если сегодня ещё не было похвалы. Это можно отключить в любой момент.
      </p>
      <div className="reminder-card__actions">
        <button
          className="primary-button"
          disabled={phase === "working"}
          onClick={() => void answer(true)}
        >
          {phase === "working" ? "Сохраняем…" : "Да, напоминай"}
        </button>
        <button
          className="secondary-button"
          disabled={phase === "working"}
          onClick={() => void answer(false)}
        >
          Не нужно
        </button>
      </div>
      {phase === "error" && (
        <p className="reminder-card__message" role="status">
          Не получилось сохранить ответ. Можно спокойно попробовать ещё раз.
        </p>
      )}
    </section>
  );
}
