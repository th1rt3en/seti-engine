import { type MouseEvent, type TouchEvent, useCallback, useEffect, useRef } from "react";
// On a touch screen there is no hovering: an enlarged picture of a card appears when the card is held for a second (a plain tap only selects it),
// and goes away by itself after a few seconds or when it is tapped.
export const touchScreen = (): boolean => typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;

/** How long an enlarged picture stays on a touch screen. */
export const ZOOM_SECONDS = 3;

/** How long a card is held on a touch screen before it is shown enlarged. */
export const LONG_PRESS_MS = 1000;
/** A finger that moves farther than this (in pixels) is scrolling, not holding. */
const MOVE_TOLERANCE = 10;

/**
 * Handlers that call `onLong` when a card is held for `LONG_PRESS_MS` on a touch screen. A tap does nothing here (the card's own click, such as
 * selecting it, still happens), and the click that follows a long press is swallowed so that holding a card does not also select it.
 */
export function useLongPress(onLong: () => void) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const fired = useRef(false);
  const callback = useRef(onLong);
  callback.current = onLong;
  const cancel = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
    start.current = null;
  }, []);
  useEffect(() => cancel, [cancel]);
  return {
    onTouchStart: (e: TouchEvent) => {
      fired.current = false;
      const touch = e.touches[0];
      if (!touch || e.touches.length > 1) return cancel();
      start.current = { x: touch.clientX, y: touch.clientY };
      timer.current = setTimeout(() => {
        timer.current = null;
        fired.current = true;
        callback.current();
      }, LONG_PRESS_MS);
    },
    onTouchMove: (e: TouchEvent) => {
      const touch = e.touches[0];
      const from = start.current;
      if (touch && from && Math.hypot(touch.clientX - from.x, touch.clientY - from.y) > MOVE_TOLERANCE) cancel();
    },
    onTouchEnd: cancel,
    onTouchCancel: cancel,
    /** The long press also opens the phone's own menu for a picture: not wanted on a card. */
    onContextMenu: (e: MouseEvent) => {
      if (touchScreen()) e.preventDefault();
    },
    /** Put this on the click of the picture (capture phase): it swallows the click that ends a long press. */
    onClickCapture: (e: MouseEvent) => {
      if (fired.current) {
        fired.current = false;
        e.stopPropagation();
        e.preventDefault();
      }
    },
  };
}
