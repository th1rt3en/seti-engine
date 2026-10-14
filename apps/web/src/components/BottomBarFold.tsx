"use client";
// On a phone the four panels (hand, card row, players, log) are tabs of a bar at the bottom of the window. This button hides the bar and the panel
// that is open, so that the whole window shows the board, and brings them back.
import { useEffect, useState } from "react";

export function BottomBarFold() {
  const [hidden, setHidden] = useState(false);
  useEffect(() => {
    document.documentElement.classList.toggle("dockbar-hidden", hidden);
    return () => document.documentElement.classList.remove("dockbar-hidden");
  }, [hidden]);
  return (
    <button type="button" className="dockbarfold" aria-expanded={!hidden} onClick={() => setHidden(!hidden)}>
      {hidden ? "▴ Panels" : "▾ Hide"}
    </button>
  );
}
