"use client";
// The player tracker as a panel floating over the page at the right edge of the window (it never pushes the board aside). It can be folded to a tab; on a narrow window it starts folded (the scores are always in the bar on top).
import { useDock } from "@/lib/useDock";
import type { ReactNode } from "react";

export function TrackerDock({ children }: { children: ReactNode }) {
  const [folded, toggle] = useDock("players", () => window.innerWidth < 1700);
  return (
    <aside className={folded ? "trackerdock dock folded" : "trackerdock dock"} aria-label="Player tracker">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Players</span>
        <span aria-hidden="true">{folded ? "◂" : "▸"}</span>
      </button>
      {folded ? null : <div className="trackerbody">{children}</div>}
    </aside>
  );
}
