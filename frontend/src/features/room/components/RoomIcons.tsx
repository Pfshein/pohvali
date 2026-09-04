/**
 * Faithful outline SVG icons for the room UI: one 24×24 grid, currentColor,
 * 1.8px stroke, round caps and joins (spec section 4). Decorative icons are
 * aria-hidden by their callers; accessible names live on the buttons.
 */

interface IconProps {
  size?: number;
}

function iconProps(size: number) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false as const,
  };
}

export function RoomHeartIcon({ size = 22 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <path d="M12 20.2 4.9 13a4.6 4.6 0 0 1 0-6.5 4.4 4.4 0 0 1 6.3 0l.8.8.8-.8a4.4 4.4 0 0 1 6.3 0 4.6 4.6 0 0 1 0 6.5Z" />
    </svg>
  );
}

export function RoomFilledHeartIcon({ size = 44 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden focusable="false">
      <path d="M12 21 4.8 13.6a5 5 0 0 1 0-7 4.8 4.8 0 0 1 6.9 0l.3.3.3-.3a4.8 4.8 0 0 1 6.9 0 5 5 0 0 1 0 7Z" />
    </svg>
  );
}

export function RoomSettingsIcon({ size = 22 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M19.3 14.6a1.6 1.6 0 0 0 .33 1.76l.06.06a1.9 1.9 0 1 1-2.7 2.7l-.06-.06a1.6 1.6 0 0 0-1.76-.33 1.6 1.6 0 0 0-1 1.47V21a1.9 1.9 0 1 1-3.8 0v-.11a1.6 1.6 0 0 0-1-1.47 1.6 1.6 0 0 0-1.76.33l-.06.06a1.9 1.9 0 1 1-2.7-2.7l.06-.06a1.6 1.6 0 0 0 .33-1.76 1.6 1.6 0 0 0-1.47-1H3a1.9 1.9 0 1 1 0-3.8h.11a1.6 1.6 0 0 0 1.47-1 1.6 1.6 0 0 0-.33-1.76l-.06-.06a1.9 1.9 0 1 1 2.7-2.7l.06.06a1.6 1.6 0 0 0 1.76.33h.01a1.6 1.6 0 0 0 1-1.47V3a1.9 1.9 0 1 1 3.8 0v.11a1.6 1.6 0 0 0 1 1.47 1.6 1.6 0 0 0 1.76-.33l.06-.06a1.9 1.9 0 1 1 2.7 2.7l-.06.06a1.6 1.6 0 0 0-.33 1.76v.01a1.6 1.6 0 0 0 1.47 1H21a1.9 1.9 0 1 1 0 3.8h-.11a1.6 1.6 0 0 0-1.47 1Z" />
    </svg>
  );
}

export function RoomCalendarIcon({ size = 24 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <rect x="3.5" y="5" width="17" height="15.5" rx="3.2" />
      <path d="M3.5 9.6h17M8 3.5v3M16 3.5v3" />
      <path d="M7.6 13.4h.01M12 13.4h.01M16.4 13.4h.01M7.6 16.8h.01M12 16.8h.01" strokeWidth={2.4} />
    </svg>
  );
}

export function RoomProfileIcon({ size = 24 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <circle cx="12" cy="8.2" r="3.9" />
      <path d="M4.8 20.4a7.6 7.6 0 0 1 14.4 0" />
    </svg>
  );
}

export function RoomFurnishIcon({ size = 20 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <path d="M6.3 4.8h11.4a2 2 0 0 1 2 2v3.1a2.6 2.6 0 0 0 0 5v3.1a2 2 0 0 1-2 2H6.3a2 2 0 0 1-2-2v-3.1a2.6 2.6 0 0 0 0-5V6.8a2 2 0 0 1 2-2Z" />
      <path d="M12 9.6v5.2M9.4 11.3h5.2" />
      <path d="M5.6 20v1.4M18.4 20v1.4" />
    </svg>
  );
}

export function RoomSparkIcon({ size = 18 }: IconProps) {
  return (
    <svg {...iconProps(size)}>
      <path d="M12 4.2 13.7 9a3 3 0 0 0 1.8 1.8l4.8 1.7-4.8 1.7A3 3 0 0 0 13.7 16L12 20.8 10.3 16a3 3 0 0 0-1.8-1.8L3.7 12.5l4.8-1.7A3 3 0 0 0 10.3 9Z" />
    </svg>
  );
}
