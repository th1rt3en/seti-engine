"use client";
// A keyboard button next to the gear in the heading of a game page; it opens an overlay that lists the keyboard shortcuts. The key "?" opens it too
// (GameClient sends the event). The list is the one that GameClient's key handler implements.
import { useEffect, useState } from "react";

export const OPEN_SHORTCUTS_EVENT = "seti-open-shortcuts";

const SHORTCUTS: { keys: string[]; text: string }[] = [
  { keys: ["Enter"], text: "Confirm the question in the context bar" },
  { keys: ["Esc"], text: "Cancel it, or close this list" },
  { keys: ["E"], text: "End the turn" },
  { keys: ["U"], text: "Take the last move back" },
  { keys: ["F"], text: "Fold or unfold all the panels" },
  { keys: ["1", "2", "3", "4"], text: "Board of the player in that pill" },
  { keys: ["Q"], text: "Hand: open or close" },
  { keys: ["W"], text: "Other cards: next tab, then close" },
  { keys: ["L"], text: "Log: open or close" },
  { keys: ["R"], text: "Player details: open or close" },
  { keys: ["?"], text: "Open this list" },
];

export function ShortcutsHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener(OPEN_SHORTCUTS_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_SHORTCUTS_EVENT, onOpen);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="gearbtn kbdbtn"
        aria-label="Keyboard shortcuts"
        aria-haspopup="dialog"
        title="Keyboard shortcuts"
        onClick={() => setOpen(true)}
      >
        ⌨
      </button>
      {open ? (
        <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)} role="presentation">
          {/* biome-ignore lint/a11y/useSemanticElements: an overlay with its own backdrop, not a native <dialog> */}
          <div className="overlaybox shortcutsbox" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
            <h2>Keyboard shortcuts</h2>
            <ul className="shortcutgrid">
              {SHORTCUTS.map((s) => (
                <li key={s.keys.join("+")}>
                  <span className="keys">
                    {s.keys.map((k) => (
                      <kbd key={k}>{k}</kbd>
                    ))}
                  </span>
                  <span>{s.text}</span>
                </li>
              ))}
            </ul>
            <p className="muted small">The keys do nothing while you type in a field or when a button has the focus (except Esc).</p>
            <button type="button" className="primary" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}
