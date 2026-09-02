import type { Mascot } from "../lib/mascots";
import { buildMonthStarArc } from "../lib/month-progress";
import { monthStarsCaption } from "../lib/plural";

interface StarArcHeroProps {
  praisedDays: ReadonlySet<number>;
  monthName: string;
  daysInMonth: number;
  mascot: Mascot;
}

export function StarArcHero({ praisedDays, monthName, daysInMonth, mascot }: StarArcHeroProps) {
  const stars = buildMonthStarArc(praisedDays, daysInMonth);
  const filledStars = stars.filter((star) => star.filled).length;
  const caption = monthStarsCaption(filledStars, monthName);

  return (
    <section className="mascot-hero" aria-label={caption}>
      <div className="star-arc" aria-hidden="true">
        <div className="rainbow-band rainbow-band--lavender" />
        <div className="rainbow-band rainbow-band--peach" />
        <div className="rainbow-band rainbow-band--green" />
        {stars.map((star, index) => (
          <span
            className={star.filled ? "arc-star arc-star--filled" : "arc-star"}
            key={index}
            style={{
              left: `${star.left}%`,
              top: `${star.top}%`,
              transform: `translate(-50%, -50%) rotate(${star.rotation}deg)`,
            }}
          >
            ★
          </span>
        ))}
      </div>

      <div className="mascot-hero__glow" aria-hidden="true" />
      <img
        className="mascot-hero__image"
        src={mascot.assetPath}
        alt={`${mascot.name} — талисман приложения`}
      />

      <div className="mascot-hero__caption">
        <span>{caption}</span>
      </div>
    </section>
  );
}
