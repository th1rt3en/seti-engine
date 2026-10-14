// On a touch screen there is no hovering: an enlarged picture appears when the picture is tapped, and goes away by itself after a few seconds or
// when it is tapped.
export const touchScreen = (): boolean => typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;

/** How long an enlarged picture stays on a touch screen. */
export const ZOOM_SECONDS = 3;
