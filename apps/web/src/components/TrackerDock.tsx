"use client";
// The player tracker as a panel floating over the page at the right edge of the window (it never pushes the board aside). It can be folded to a tab; on a narrow window it starts folded (the scores are always in the bar on top).
// On a screen that is not tall or wide enough for the whole table the panel is made smaller to fit: everything shows without scrolling (down to a limit, below which it scrolls).
import { isPhone, useDock } from "@/lib/useDock";
import { type ReactNode, useLayoutEffect, useRef } from "react";

/** The smallest the table is made: below it the text is too small to read, and the panel scrolls. */
const MIN_ZOOM = 0.45;

export function TrackerDock({ children }: { children: ReactNode }) {
  const [folded, toggle] = useDock("players", () => window.innerWidth < 1700);
  const body = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  // fit the table into the height that is left under the bar, on a window that is not a phone (there the panel is a sheet that scrolls)
  useLayoutEffect(() => {
    const box = body.current;
    const content = inner.current;
    if (folded || !box || !content) return;
    const fit = () => {
      if (isPhone()) {
        content.style.removeProperty("zoom");
        return;
      }
      content.style.setProperty("zoom", "1");
      const natural = content.offsetHeight;
      const wide = content.scrollWidth; // the table is as wide as its columns need (it does not shrink to the panel)
      const top = box.getBoundingClientRect().top;
      const room = window.innerHeight - top - 14 - 8; // the margin under the panel and its padding
      const across = box.clientWidth - 16; // the width of the panel without its padding
      const byHeight = natural <= 0 ? 1 : room / natural;
      const byWidth = wide <= 0 ? 1 : across / wide;
      const zoom = Math.max(MIN_ZOOM, Math.min(1, byHeight, byWidth));
      content.style.setProperty("zoom", String(Math.round(zoom * 100) / 100));
    };
    fit();
    const watch = new ResizeObserver(fit);
    watch.observe(document.documentElement);
    watch.observe(content); // the table grows when a species or an organization comes into the game
    window.addEventListener("resize", fit);
    return () => {
      watch.disconnect();
      window.removeEventListener("resize", fit);
    };
  }, [folded]);
  return (
    <aside className={folded ? "trackerdock dock folded" : "trackerdock dock"} aria-label="Player tracker">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Players</span>
        <span aria-hidden="true">{folded ? "◂" : "▸"}</span>
      </button>
      {folded ? null : (
        <div className="trackerbody" ref={body}>
          <div ref={inner} style={{ width: "max-content", minWidth: "100%" }}>
            {children}
          </div>
        </div>
      )}
    </aside>
  );
}
