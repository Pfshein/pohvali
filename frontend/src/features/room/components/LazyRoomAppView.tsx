import { lazy } from "react";

/**
 * The single dynamic import boundary of the room feature: everything Pixi and
 * room-related is reachable only through this lazy component, so the classic
 * initial bundle stays free of PixiJS.
 */
export const LazyRoomAppView = lazy(() =>
  import("./RoomAppView").then((module) => ({ default: module.RoomAppView })),
);
