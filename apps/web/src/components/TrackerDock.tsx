"use client";
// The player tracker as a panel floating over the page at the right edge of the window (it never pushes the board aside). It can be folded to a tab; on a narrow window it starts folded (the scores are always in the bar on top).
import { type ReactNode, useEffect, useState } from "react";

const KEY = "seti-tracker-folded";

export function TrackerDock({ children }: { children: ReactNode }) {
  const [folded, setFolded] = useState(false);
  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      setFolded(saved === null ? window.innerWidth < 2300 : saved === "1");
    } catch {
      setFolded(window.innerWidth < 2300);
    }
  }, []);
  const toggle = () => {
    const next = !folded;
    setFolded(next);
    try {
      localStorage.setItem(KEY, next ? "1" : "0");
    } catch {
      // not remembered
    }
  };
  return (
    <aside className={folded ? "trackerdock folded" : "trackerdock"} aria-label="Player tracker">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Players</span>
        <span aria-hidden="true">{folded ? "◂" : "▸"}</span>
      </button>
      {folded ? null : <div className="trackerbody">{children}</div>}
    </aside>
  );
}
