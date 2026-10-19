"use client";
// On a phone the bar on top (counters, who is to act, scores, the moves) takes a good part of the screen: this button folds it down to the counters and
// the question that the game asks, and opens it again.
import { isPhone } from "@/lib/useDock";
import { useEffect, useState } from "react";

export function BarFold() {
  const [collapsed, setCollapsed] = useState(false);
  // on a phone the page starts with the bar folded down to the counters and the question that the game asks
  useEffect(() => {
    if (isPhone()) setCollapsed(true);
  }, []);
  useEffect(() => {
    document.querySelector(".topbar")?.classList.toggle("collapsed", collapsed);
    return () => document.querySelector(".topbar")?.classList.remove("collapsed");
  }, [collapsed]);
  return (
    <button type="button" className="barfold ghost small" aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}>
      {collapsed ? "▾ Moves" : "▴ Hide"}
    </button>
  );
}
