"use client";
// A "ting" when it becomes the player's turn to act while the page is open (D34). The sound is made with the Web Audio API, so there is no file.
// Browsers only allow sound after the person has touched the page once: the first click, tap or key press unlocks it. The player can switch the
// sound off; that is remembered in this browser.
import { useCallback, useEffect, useRef, useState } from "react";

const KEY = "seti-turn-sound";
let context: AudioContext | null = null;

function audio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (context === null) {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    context = new Ctor();
  }
  return context;
}

/** Make the sound available after the first touch of the page. */
function unlockOnFirstTouch(): () => void {
  const unlock = () => {
    void audio()?.resume();
  };
  const events = ["pointerdown", "keydown", "touchstart"] as const;
  for (const e of events) window.addEventListener(e, unlock, { once: true, passive: true });
  return () => {
    for (const e of events) window.removeEventListener(e, unlock);
  };
}

/** A short bell: two soft partials that fade out in about a second. */
export function ting(): void {
  const ctx = audio();
  if (!ctx || ctx.state !== "running") return;
  const now = ctx.currentTime;
  for (const [hz, volume] of [
    [1568, 0.22],
    [2349, 0.09],
  ] as const) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = hz;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(volume, now + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 1.1);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 1.2);
  }
}

/**
 * Plays the ting when `myTurn` turns from false to true, and puts "Your turn" in front of the tab title while it is the player's turn.
 * Returns whether the sound is on and a function to switch it.
 */
export function useTurnSound(myTurn: boolean): [boolean, () => void] {
  const [on, setOn] = useState(true);
  const onRef = useRef(true);
  const previous = useRef<boolean | null>(null);
  const baseTitle = useRef<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved !== null) {
        setOn(saved === "1");
        onRef.current = saved === "1";
      }
    } catch {
      // not remembered
    }
    return unlockOnFirstTouch();
  }, []);

  useEffect(() => {
    if (previous.current === false && myTurn && onRef.current) ting();
    previous.current = myTurn;
  }, [myTurn]);

  useEffect(() => {
    if (baseTitle.current === null) baseTitle.current = document.title;
    const base = baseTitle.current.replace(/^● Your turn · /, "");
    document.title = myTurn ? `● Your turn · ${base}` : base;
    return () => {
      document.title = base;
    };
  }, [myTurn]);

  const toggle = useCallback(() => {
    const next = !onRef.current;
    onRef.current = next;
    setOn(next);
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      // not remembered
    }
    if (next) {
      void audio()?.resume();
      ting();
    }
  }, []);

  return [on, toggle];
}
