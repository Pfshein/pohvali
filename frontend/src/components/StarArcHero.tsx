import avocadoMascot from "../assets/avocado-mascot.png";
import { buildMonthStarArc } from "../lib/month-progress";

interface StarArcHeroProps {
  praisedDays: ReadonlySet<number>;
  monthName: string;
  daysInMonth: number;
}

export function StarArcHero({ praisedDays, monthName, daysInMonth }: StarArcHeroProps) {
  const stars = buildMonthStarArc(praisedDays, daysInMonth);
  const filledStars = stars.filter((star) => star.filled).length;

  return (
    <section className="mascot-hero" aria-label={`${filledStars} звёзд в ${monthName}`}>
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
        src={avocadoMascot}
        alt="Авокадо — талисман приложения"
      />

      <div className="mascot-hero__caption">
        <strong>Авокадо Ава</strong>
        <span>Уже {filledStars} звёзд в {monthName}</span>
      </div>
    </section>
  );
}
