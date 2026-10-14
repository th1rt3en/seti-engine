"use client";
// The title of a group of moves in the action bar. On a phone the group of free actions can be folded down so that the bar leaves more of the
// board visible; whether it is folded is remembered in this browser. On a wide window the title is a plain label and nothing folds.
import { useEffect, useState } from "react";

const KEY = "seti-free-actions-folded";

export function useFoldableGroup(foldable: boolean): [boolean, () => void] {
  const [folded, setFolded] = useState(false);
  useEffect(() => {
    if (!foldable) return;
    try {
      setFolded(localStorage.getItem(KEY) === "1");
    } catch {
      // not remembered
    }
  }, [foldable]);
  const toggle = () => {
    setFolded(!folded);
    try {
      localStorage.setItem(KEY, folded ? "0" : "1");
    } catch {
      // not remembered
    }
  };
  return [folded, toggle];
}

export function MoveGroup({
  title,
  count,
  foldable,
  children,
}: { title: string; count: number; foldable: boolean; children: React.ReactNode }) {
  const [folded, toggle] = useFoldableGroup(foldable);
  return (
    <div className={foldable && folded ? "mgroup foldable folded" : foldable ? "mgroup foldable" : "mgroup"}>
      {foldable ? (
        <button type="button" className="glabel groupfold" aria-expanded={!folded} onClick={toggle}>
          {title} ({count}) <span aria-hidden="true">{folded ? "▾" : "▴"}</span>
        </button>
      ) : (
        <span className="glabel">{title}</span>
      )}
      {children}
    </div>
  );
}
