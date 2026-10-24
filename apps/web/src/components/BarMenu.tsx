"use client";
// The hamburger menu at the end of the bar of a game: what is rarely needed and could be pressed by mistake (resigning), and the way back to the rest of the
// site while the site's own bar is hidden during a game.
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

export function BarMenu({
  onResign,
  siteShown,
  onToggleSite,
}: {
  /** Present when the player may resign (a player of a game that is not over). */
  onResign?: () => void;
  siteShown: boolean;
  onToggleSite: () => void;
}) {
  const [open, setOpen] = useState(false);
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
