/**
 * Russian pluralisation.
 *
 * Counts reach the screen from praise totals and mascot prices, and a hard
 * coded "звёзд" reads wrong for most of them ("1 звёзд"). Every user-facing
 * count goes through here instead.
 */
export function pluralRu(count: number, one: string, few: string, many: string): string {
  const absolute = Math.abs(Math.trunc(count));
  const lastTwo = absolute % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return many;
  const last = absolute % 10;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

/** "1 звезда", "3 звезды", "5 звёзд". */
export function starsWithCount(count: number): string {
  return `${count} ${pluralRu(count, "звезда", "звезды", "звёзд")}`;
}

/**
 * The line under the mascot. A star stands for one moment of choosing
 * yourself, so the caption names what the count is, never who earned it — the
 * mascot is company, not the subject of the sentence.
 */
export function monthStarsCaption(count: number, monthName: string): string {
  if (count <= 0) return `В ${monthName} пока тихо. Первая звезда впереди`;
  // "моменты" describes the whole set of stars rather than agreeing with the
  // numeral, so it is singular only for exactly one — 21 stars are 21 moments,
  // even though the numeric rule would inflect 21 as a singular.
  const moments = count === 1 ? "момент, когда" : "моменты, когда";
  return `${starsWithCount(count)} в ${monthName} — ${moments} ты выбираешь себя`;
}
