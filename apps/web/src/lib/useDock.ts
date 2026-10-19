"use client";
// The fold state of the floating panels (hand, card row, players, log). On a wide window each panel remembers in this browser whether it is
// folded. On a phone the four panels are tabs of one bar at the bottom, and opening one folds the others.
import { type RefObject, useEffect, useState } from "react";

const PHONE = 760;
const EVENT = "seti-dock-open";
export const ALL_EVENT = "seti-dock-all";

export const isPhone = (): boolean => typeof window !== "undefined" && window.innerWidth <= PHONE;

export function useDock(name: string, startFolded: () => boolean = () => false): [boolean, () => void, (open: boolean) => void] {
  const [folded, setFolded] = useState(false);
  // biome-ignore lint/correctness/useExhaustiveDependencies: read the saved state once, when the page has loaded
  useEffect(() => {
    if (isPhone()) {
      setFolded(true);
      return;
    }
    try {
      const saved = localStorage.getItem(`seti-dock-${name}`);
      setFolded(saved === null ? startFolded() : saved === "1");
    } catch {
      setFolded(startFolded());
    }
  }, [name]);
  useEffect(() => {
    const onOpen = (e: Event) => {
      if ((e as CustomEvent<string>).detail !== name && isPhone()) setFolded(true);
    };
    window.addEventListener(EVENT, onOpen);
    return () => window.removeEventListener(EVENT, onOpen);
  }, [name]);
  // the key "f" folds or unfolds every panel at once (components/GameClient.tsx)
  useEffect(() => {
    const onAll = (e: Event) => {
      const open = (e as CustomEvent<boolean>).detail;
      setFolded(!open);
      if (!isPhone()) {
        try {
          localStorage.setItem(`seti-dock-${name}`, open ? "0" : "1");
        } catch {
          // not remembered
        }
      }
    };
    window.addEventListener(ALL_EVENT, onAll);
    return () => window.removeEventListener(ALL_EVENT, onAll);
  }, [name]);
  const set = (open: boolean) => {
    setFolded(!open);
    if (open) window.dispatchEvent(new CustomEvent(EVENT, { detail: name }));
    if (!isPhone()) {
      try {
        localStorage.setItem(`seti-dock-${name}`, open ? "0" : "1");
      } catch {
        // not remembered
      }
    }
  };
  return [folded, () => set(folded), set];
}

/**
 * Keeps room at the bottom of the page for a panel that floats there, so that the page can be scrolled until what the panel covers is in view.
 * The panel's height goes to a CSS variable (`--<name>-h`); the page's bottom padding follows it. On a phone the panels are a bar and sheets
 * of their own, so no room is kept.
 */
export function useBottomSpace(ref: RefObject<HTMLElement | null>, name: string): void {
  useEffect(() => {
    const el = ref.current;
    const root = document.documentElement;
    if (!el) return;
    const set = () => root.style.setProperty(`--${name}-h`, isPhone() ? "0px" : `${el.offsetHeight}px`);
    set();
    const watch = new ResizeObserver(set);
    watch.observe(el);
    window.addEventListener("resize", set);
    return () => {
      watch.disconnect();
      window.removeEventListener("resize", set);
      root.style.setProperty(`--${name}-h`, "0px");
    };
  }, [ref, name]);
}
