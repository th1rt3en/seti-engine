"use client";
// The title of a group of moves in the action bar. On a phone the groups of free actions and of moving a probe can be folded down so that the bar
// leaves more of the board visible. Both start folded; whether the player opened one is remembered in this browser. On a wide window the title is
// a plain label and nothing folds.
import { type ReactNode, useEffect, useState } from "react";

const key = (title: string): string => `seti-group-open-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;

export function useFoldableGroup(title: string, foldable: boolean): [boolean, () => void] {
  const [folded, setFolded] = useState(true); // collapsed by default
  useEffect(() => {
    if (!foldable) return;
    try {
      setFolded(localStorage.getItem(key(title)) !== "1");
    } catch {
      // not remembered
    }
  }, [title, foldable]);
  const toggle = () => {
    setFolded(!folded);
    try {
      localStorage.setItem(key(title), folded ? "1" : "0");
    } catch {
      // not remembered
    }
  };
  return [folded, toggle];
}

/** `forceOpen`: the group shows although it is folded (a probe has been picked on the board, so its move budget is needed). */
export function MoveGroup({
  title,
  count,
  foldable,
  forceOpen = false,
  className = "",
  children,
}: { title: string; count?: number; foldable: boolean; forceOpen?: boolean; className?: string; children: ReactNode }) {
  const [foldedState, toggle] = useFoldableGroup(title, foldable);
  const folded = foldedState && !forceOpen;
  const classes = ["mgroup", className, foldable ? "foldable" : "", foldable && folded ? "folded" : ""].filter(Boolean).join(" ");
  return (
    <div className={classes}>
      {foldable ? (
        <button type="button" className="glabel groupfold" aria-expanded={!folded} onClick={toggle}>
          {title}
          {count === undefined ? "" : ` (${count})`} <span aria-hidden="true">{folded ? "▾" : "▴"}</span>
        </button>
      ) : (
        <span className="glabel">{title}</span>
      )}
      {children}
    </div>
  );
}
