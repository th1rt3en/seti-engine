"use client";
// Keeps the CSS variable --bar-h at the height of the sticky bar on top of the game page, so that the panels beside the board
// (tracker, publicity track and tech stacks) start right below it and fit in the rest of the window.
import { useEffect } from "react";

export function BarHeight() {
  useEffect(() => {
    const bar = document.querySelector<HTMLElement>(".topbar");
    if (!bar) return;
    const set = () => document.documentElement.style.setProperty("--bar-h", `${bar.getBoundingClientRect().height}px`);
    set();
    const observer = new ResizeObserver(set);
    observer.observe(bar);
    return () => observer.disconnect();
  }, []);
  return null;
}
