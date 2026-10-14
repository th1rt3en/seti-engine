"use client";
// Keeps two CSS variables up to date for the panels that float beside the board (tracker, card row): --bar-h is the height of the sticky bar on
// top of the game page, and --bar-bottom is where its lower edge is in the window now (the site's own header scrolls away above it), so that
// the panels always start right below the bar and never cover its moves.
import { useEffect } from "react";

export function BarHeight() {
  useEffect(() => {
    const bar = document.querySelector<HTMLElement>(".topbar");
    if (!bar) return;
    const root = document.documentElement;
    const set = () => {
      const box = bar.getBoundingClientRect();
      root.style.setProperty("--bar-h", `${box.height}px`);
      root.style.setProperty("--bar-bottom", `${Math.max(0, box.bottom)}px`);
    };
    set();
    const observer = new ResizeObserver(set);
    observer.observe(bar);
    window.addEventListener("scroll", set, { passive: true });
    window.addEventListener("resize", set);
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", set);
      window.removeEventListener("resize", set);
    };
  }, []);
  return null;
}
