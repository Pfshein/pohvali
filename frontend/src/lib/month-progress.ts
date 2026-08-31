export interface ArcStar {
  day: number;
  filled: boolean;
  left: number;
  top: number;
  rotation: number;
}

export function buildMonthStarArc(
  praisedDays: ReadonlySet<number>,
  daysInMonth: number,
): ArcStar[] {
  const normalizedDays = Number.isFinite(daysInMonth) ? Math.floor(daysInMonth) : 31;
  const total = Math.min(31, Math.max(28, normalizedDays));
  const startAngle = 200;
  const endAngle = 340;

  return Array.from({ length: total }, (_, index) => {
    const day = index + 1;
    const progress = total === 1 ? 0.5 : index / (total - 1);
    const angle = startAngle + (endAngle - startAngle) * progress;
    const radians = (angle * Math.PI) / 180;

    return {
      day,
      filled: praisedDays.has(day),
      left: 50 + Math.cos(radians) * 47,
      top: 58 + Math.sin(radians) * 50,
      rotation: -10 + progress * 20,
    };
  });
}
