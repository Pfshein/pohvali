import type { MascotItem } from "../lib/mascots-api";
import { starsWithCount } from "../lib/plural";

interface CollectionProps {
  mascots: readonly MascotItem[];
  balance: number;
  busyCode?: string | null;
  onPurchase: (code: string) => void;
  onActivate: (code: string) => void;
}

function lockedHint(mascot: MascotItem): string {
  if (mascot.price === null) return "Скоро будет рядом";
  return mascot.unlocked
    ? `Почти — нужно ⭐${mascot.price}`
    : `Появится ближе к ⭐${mascot.price}`;
}

export function Collection({
  mascots,
  balance,
  busyCode,
  onPurchase,
  onActivate,
}: CollectionProps) {
  return (
    <section className="collection" aria-labelledby="collection-title">
      <header className="collection__head">
        <div>
          <p className="eyebrow">Твои спутники</p>
          <h2 id="collection-title">Коллекция</h2>
        </div>
        <div className="star-balance" aria-label={starsWithCount(balance)}>
          <span aria-hidden="true">★</span><b>{balance}</b>
        </div>
      </header>

      <p className="collection__note">
        Спутники открываются в своём темпе — торопиться некуда.
      </p>

      <ul className="collection__grid">
        {mascots.map((mascot) => {
          const busy = busyCode === mascot.code;
          return (
            <li
              key={mascot.code}
              className={
                mascot.active ? "mascot-card mascot-card--active" : "mascot-card"
              }
            >
              <img
                className={mascot.state === "locked" ? "mascot-card__image mascot-card__image--dim" : "mascot-card__image"}
                src={mascot.assetPath}
                alt=""
                aria-hidden="true"
              />
              <div className="mascot-card__copy">
                <strong>{mascot.name}</strong>
                <span>{mascot.blurb}</span>
              </div>

              {mascot.state === "owned" && mascot.active && (
                <span className="mascot-card__badge" aria-label="Рядом сейчас">
                  Рядом сейчас
                </span>
              )}

              {mascot.state === "owned" && !mascot.active && (
                <button
                  className="secondary-button mascot-card__action"
                  disabled={busy}
                  onClick={() => onActivate(mascot.code)}
                  aria-label={`Выбрать: ${mascot.name}`}
                >
                  {busy ? "Выбираем…" : "Выбрать"}
                </button>
              )}

              {mascot.state === "affordable" && (
                <button
                  className="primary-button mascot-card__action"
                  disabled={busy}
                  onClick={() => onPurchase(mascot.code)}
                  aria-label={`Открыть ${mascot.name} за ${starsWithCount(mascot.price ?? 0)}`}
                >
                  {busy ? "Открываем…" : `Открыть за ⭐${mascot.price ?? 0}`}
                </button>
              )}

              {mascot.state === "locked" && (
                <span className="mascot-card__hint">{lockedHint(mascot)}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
