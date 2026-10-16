"use client";
// The reminder of what to do with the moves that are offered, kept out of the way: a small ? button that shows the text when it is pressed.
import { type ReactNode, useState } from "react";

export function Hint({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="hint">
      <button
        type="button"
        className="hintbtn"
        aria-expanded={open}
        aria-label="What can I do here?"
        title="What can I do here?"
        onClick={() => setOpen(!open)}
      >
        ?
      </button>
      {open ? (
        // biome-ignore lint/a11y/useKeyWithClickEvents: it can also be closed with the button
        <span className="hinttext" role="note" onClick={() => setOpen(false)}>
          {children}
        </span>
      ) : null}
    </span>
  );
}
