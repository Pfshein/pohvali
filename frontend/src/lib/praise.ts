export const MAX_PRAISE_LENGTH = 500;
export const MIN_PRAISE_LENGTH = 4;

const HAS_LETTER = /\p{L}/u;

export function normalizePraise(value: string): string {
  return value.trim();
}

export function isValidPraise(value: string): boolean {
  const normalized = normalizePraise(value);
  return (
    normalized.length >= MIN_PRAISE_LENGTH &&
    normalized.length <= MAX_PRAISE_LENGTH &&
    HAS_LETTER.test(normalized)
  );
}

