"use client";
// The hamburger menu at the end of the bar of a game: what is rarely needed and could be pressed by mistake (resigning), and the way back to the rest of the
// site while the site's own bar is hidden during a game.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

/** How many moves a proposal may ask to take back (the Worker's UNDO_MAX). */
const UNDO_MAX = 10;

export function BarMenu({
  onResign,
  onPropose,
  coolUntil,
  siteShown,
  onToggleSite,
}: {
  /** Present for a player of a game that is being played: asks the others to take back the last `count` moves. */
  onPropose?: (count: number) => void;
  /** When this player can propose again (null: now). */
  coolUntil?: number | null;
  /** Present when the player may resign (a player of a game that is not over). */
  onResign?: () => void;
  siteShown: boolean;
  onToggleSite: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [asking, setAsking] = useState(false);
  const [count, setCount] = useState(1);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!open) return;
    setNow(Date.now());
    const t = setInterval(() => setNow(Date.now()), 15_000);
    return () => clearInterval(t);
  }, [open]);
  const wait = coolUntil && coolUntil > now ? Math.ceil((coolUntil - now) / 60_000) : 0;
  const box = useRef<HTMLSpanElement>(null);
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
    <span className="barmenu" ref={box}>
      <button
        type="button"
        className="gearbtn"
        aria-label="Menu"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Menu"
        onClick={() => setOpen(!open)}
      >
        ☰
      </button>
      {open ? (
        <div className="barmenupanel" role="menu">
          <Link href="/lobby" role="menuitem" onClick={() => setOpen(false)}>
            Back to the lobby
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              onToggleSite();
              setOpen(false);
            }}
          >
            {siteShown ? "Hide the site bar" : "Show the site bar"}
          </button>
          {onPropose ? (
            <>
              <button type="button" role="menuitem" disabled={wait > 0} aria-expanded={asking} onClick={() => setAsking(!asking)}>
                {wait > 0 ? `Propose undo (in ${wait} min)` : "Propose undo"}
              </button>
              {asking && wait === 0 ? (
                <form
                  className="undoform"
                  onSubmit={(e) => {
                    e.preventDefault();
                    onPropose(count);
                    setAsking(false);
                    setOpen(false);
                  }}
                >
                  <label>
                    Moves to take back (1 to {UNDO_MAX})
                    <input
                      type="number"
                      min={1}
                      max={UNDO_MAX}
                      value={count}
                      onChange={(e) => setCount(Math.max(1, Math.min(UNDO_MAX, Math.floor(Number(e.target.value)) || 1)))}
                    />
                  </label>
                  <button type="submit">Ask the other players</button>
                </form>
              ) : null}
            </>
          ) : null}
          {onResign ? (
            <button
              type="button"
              role="menuitem"
              className="menudanger"
              onClick={() => {
                setOpen(false);
                onResign();
              }}
            >
              Resign the game
            </button>
          ) : null}
        </div>
      ) : null}
    </span>
  );
}
