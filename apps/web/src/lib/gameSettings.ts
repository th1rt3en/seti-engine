"use client";
// The player's settings for the game page, kept in this browser (localStorage): the "ting" when it is their turn, and the size of the cards in the
// hand. Every component that uses a setting is told when it changes (an event on the window), so the gear menu in the heading of the page and the game
// below it stay in step.
import { useCallback, useSyncExternalStore } from "react";

export const SOUND_KEY = "seti-turn-sound"; // "1" or "0" (it was already kept under this name)
export const CONFIRM_KEY = "seti-confirm-irreversible"; // "1" (ask, the default) or "0": moves that cannot be undone are made at once
export const NOTIFY_KEY = "seti-turn-notify"; // "1": a browser notification when it is my turn and the tab is in the background (off by default)
export const ANIM_KEY = "seti-animations"; // "1" (the default) or "0": short animations on the board
export const PUBLICITY_KEY = "seti-publicity-track"; // "1" (shown, the default) or "0": the publicity track in the right column is hidden
export const HAND_SCALE_KEY = "seti-hand-scale"; // a number: 1 is the normal size
export const HAND_SCALE = { min: 0.7, max: 1.6, step: 0.1 };
const EVENT = "seti-settings";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // not remembered
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // not remembered
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The size factor kept in the browser, kept inside its limits. */
export function parseScale(raw: string | null): number {
  const n = raw === null ? 1 : Number(raw);
  return Number.isFinite(n) ? Math.min(HAND_SCALE.max, Math.max(HAND_SCALE.min, n)) : 1;
}

export function useGameSettings(): {
  sound: boolean;
  setSound: (on: boolean) => void;
  handScale: number;
  setHandScale: (scale: number) => void;
  /** Ask for a confirmation before a move that cannot be taken back (UNDO-01). */
  confirmIrreversible: boolean;
  setConfirmIrreversible: (on: boolean) => void;
  notify: boolean;
  setNotify: (on: boolean) => void;
  animations: boolean;
  setAnimations: (on: boolean) => void;
  /** Show the publicity track in the column at the right of the board (the publicity of everybody is in the pills anyway). */
  publicityTrack: boolean;
  setPublicityTrack: (on: boolean) => void;
} {
  const sound = useSyncExternalStore(
    subscribe,
    () => read(SOUND_KEY) !== "0",
    () => true,
  );
  const handScaleRaw = useSyncExternalStore(
    subscribe,
    () => read(HAND_SCALE_KEY),
    () => null,
  );
  const confirmIrreversible = useSyncExternalStore(
    subscribe,
    () => read(CONFIRM_KEY) !== "0",
    () => true,
  );
  const notify = useSyncExternalStore(
    subscribe,
    () => read(NOTIFY_KEY) === "1",
    () => false,
  );
  const animations = useSyncExternalStore(
    subscribe,
    () => read(ANIM_KEY) !== "0",
    () => true,
  );
  const publicityTrack = useSyncExternalStore(
    subscribe,
    () => read(PUBLICITY_KEY) !== "0",
    () => true,
  );
  const setPublicityTrack = useCallback((on: boolean) => write(PUBLICITY_KEY, on ? "1" : "0"), []);
  const setAnimations = useCallback((on: boolean) => write(ANIM_KEY, on ? "1" : "0"), []);
  const setNotify = useCallback((on: boolean) => write(NOTIFY_KEY, on ? "1" : "0"), []);
  const setConfirmIrreversible = useCallback((on: boolean) => write(CONFIRM_KEY, on ? "1" : "0"), []);
  const setSound = useCallback((on: boolean) => write(SOUND_KEY, on ? "1" : "0"), []);
  const setHandScale = useCallback((scale: number) => write(HAND_SCALE_KEY, String(parseScale(String(scale)))), []);
  return {
    sound,
    setSound,
    handScale: parseScale(handScaleRaw),
    setHandScale,
    confirmIrreversible,
    setConfirmIrreversible,
    notify,
    setNotify,
    animations,
    setAnimations,
    publicityTrack,
    setPublicityTrack,
  };
}
