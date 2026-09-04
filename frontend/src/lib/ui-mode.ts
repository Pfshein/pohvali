export type UiMode = "classic" | "room";
export const UI_MODE_STORAGE_KEY = "pohvala.ui-mode.v1";

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function parseUiModePreference(raw: string | null): UiMode {
  if (!raw) return "classic";
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null) return "classic";
    const record = value as Record<string, unknown>;
    return record.schemaVersion === 1 && (record.mode === "classic" || record.mode === "room")
      ? record.mode
      : "classic";
  } catch {
    return "classic";
  }
}

export function loadUiMode(storage: StorageLike): UiMode {
  try { return parseUiModePreference(storage.getItem(UI_MODE_STORAGE_KEY)); }
  catch { return "classic"; }
}

export function saveUiMode(mode: UiMode, storage: StorageLike): void {
  try { storage.setItem(UI_MODE_STORAGE_KEY, JSON.stringify({ schemaVersion: 1, mode })); }
  catch { /* preference is best effort */ }
}
