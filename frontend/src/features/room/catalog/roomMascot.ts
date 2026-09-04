import { findMascot } from "../../../lib/mascots";
import type { MascotCollection } from "../../../lib/mascots-api";
import type { RoomMascotAsset } from "./roomCatalog";

/**
 * Picks the mascot the room seats. The live collection answer wins (it
 * includes admin-added assets); until it arrives — or if it failed — the
 * existing local list is the calm fallback, never a crash.
 */
export function resolveRoomMascot(
  collection: MascotCollection | null,
  activeCode: string | null | undefined,
): RoomMascotAsset {
  // The locally activated code is the freshest answer: activate() sets it
  // before the collection reload lands, and that reload may fail entirely.
  // The collection is still what supplies name/assetPath for admin mascots.
  const wanted = activeCode ?? collection?.activeMascot;
  const activeEntry = wanted
    ? collection?.mascots.find((mascot) => mascot.code === wanted)
    : undefined;
  if (activeEntry) {
    return {
      code: activeEntry.code,
      name: activeEntry.name,
      assetPath: activeEntry.assetPath,
    };
  }
  const local = findMascot(activeCode);
  return { code: local.code, name: local.name, assetPath: local.assetPath };
}
