import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { RoomHeartIcon } from "./RoomIcons";
import { nextFocusableIndex } from "./focusCycle";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

interface RoomSheetProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/**
 * Accessible bottom sheet over the room: a labelled modal dialog with a close
 * control, Escape/scrim dismissal, a Tab trap and focus restoration to the
 * button that opened it. The room underneath never unmounts.
 */
export function RoomSheet({ title, onClose, children }: RoomSheetProps) {
  const headingId = useId();
  const dialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const sheet = dialogRef.current;
    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    sheet?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)?.focus();

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !sheet) return;
      const focusables = Array.from(sheet.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
        .filter((element) => element.offsetParent !== null || element === document.activeElement);
      if (focusables.length === 0) return;
      const current = focusables.indexOf(document.activeElement as HTMLElement);
      const next = nextFocusableIndex(current === -1 ? 0 : current, focusables.length, event.shiftKey ? -1 : 1);
      event.preventDefault();
      focusables[next]?.focus();
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  function stopTrap(event: KeyboardEvent) {
    if (event.key === "Escape") onClose();
  }

  return (
    <div className="room-sheet-scrim" role="presentation" onMouseDown={onClose}>
      <section
        className="room-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        ref={dialogRef}
        onKeyDown={stopTrap}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="room-sheet__handle" aria-hidden="true" />
        <header className="room-sheet__head">
          <span className="room-sheet__heart" aria-hidden="true"><RoomHeartIcon size={20} /></span>
          <h2 id={headingId}>{title}</h2>
          <button type="button" className="room-sheet__close" aria-label="Закрыть" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" aria-hidden="true" focusable="false">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>
        <div className="room-sheet__body">{children}</div>
      </section>
    </div>
  );
}
