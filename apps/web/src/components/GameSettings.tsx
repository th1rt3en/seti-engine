"use client";
// The gear button in the heading of a game page, with the player's settings for it: the sound when it is their turn and the size of the cards in the
// hand. They are kept in this browser. The size is a factor that the hand's CSS multiplies its card widths by (`--hand-scale`).
import { HAND_SCALE, useGameSettings } from "@/lib/gameSettings";
import { ting } from "@/lib/turnSound";
import { useEffect, useRef, useState } from "react";

export function GameSettings() {
  const { sound, setSound, handScale, setHandScale, confirmIrreversible, setConfirmIrreversible } = useGameSettings();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLSpanElement>(null);

  // the size of the cards in the hand, for the whole page
  useEffect(() => {
    document.documentElement.style.setProperty("--hand-scale", String(handScale));
  }, [handScale]);

  // the panel closes with a click outside it or with Escape
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent | TouchEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("touchstart", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("touchstart", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className="gamesettings" ref={box}>
      <button
        type="button"
        className="gearbtn"
        aria-label="Game settings"
        aria-expanded={open}
        title="Settings"
        onClick={() => setOpen(!open)}
      >
        ⚙
      </button>
      {open ? (
        <div className="settingspanel" role="dialog" aria-label="Game settings">
          <label className="row">
            <input
              type="checkbox"
              checked={sound}
              onChange={(e) => {
                setSound(e.target.checked);
                if (e.target.checked) ting(); // a sample of the sound
              }}
            />{" "}
            Play a ting when it is my turn
          </label>
          <label className="row">
            <input type="checkbox" checked={confirmIrreversible} onChange={(e) => setConfirmIrreversible(e.target.checked)} /> Ask me to
            confirm a move that cannot be undone
          </label>
          <label className="stack">
            <span>
              Size of the cards in my hand <b>{Math.round(handScale * 100)}%</b>
            </span>
            <input
              type="range"
              min={HAND_SCALE.min}
              max={HAND_SCALE.max}
              step={HAND_SCALE.step}
              value={handScale}
              onChange={(e) => setHandScale(Number(e.target.value))}
              aria-label="Size of the cards in my hand"
            />
          </label>
          <button type="button" className="secondary small" onClick={() => setHandScale(1)} disabled={handScale === 1}>
            Reset the size
          </button>
        </div>
      ) : null}
    </span>
  );
}
