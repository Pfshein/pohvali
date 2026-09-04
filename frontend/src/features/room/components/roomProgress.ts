/**
 * Progress wording replaces the mockup's streak pill: it counts marked days
 * of the current month and never speaks of consecutive days.
 */
export function roomProgressCaption(count: number): string {
  if (count === 0) return "Сегодня можно начать";
  if (count === 1) return "1 день заботы о себе";
  if (count >= 2 && count <= 4) return `${count} дня заботы о себе`;
  return `${count} дней заботы о себе`;
}
