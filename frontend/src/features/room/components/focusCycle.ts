/** Pure Tab-cycle math so focus trapping stays testable without a DOM. */
export function nextFocusableIndex(current: number, count: number, delta: 1 | -1): number {
  if (count === 0) return current;
  return (current + delta + count) % count;
}
