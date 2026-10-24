"use client";
// A short explanation that opens when the pointer rests on the text (a mouse), when it has the focus (a keyboard), or when it is pressed for a moment (a finger);
// on a phone it stays open until the next touch elsewhere, or for a few seconds, so that it can be read with the finger lifted.
import { type ReactNode, useEffect, useRef, useState } from "react";

const PRESS_MS = 350;
const STAY_MS = 6000;

export function HelpTip({ tip, children, className }: { tip: ReactNode; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(false);
  const press = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stay = useRef<ReturnType<typeof setTimeout> | null>(null);
  const box = useRef<HTMLSpanElement | null>(null);
  useEffect(() => {
    if (!open) return;
    // a touch anywhere else closes it
    const away = (e: Event) => {
      if (box.current && e.target instanceof Node && !box.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", away);
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);
  useEffect(
    () => () => {
      if (press.current !== null) clearTimeout(press.current);
      if (stay.current !== null) clearTimeout(stay.current);
    },
    [],
  );
  const clearPress = () => {
    if (press.current !== null) clearTimeout(press.current);
    press.current = null;
  };
  return (
    <span
      ref={box}
      className={className ? `helptip ${className}` : "helptip"}
      // biome-ignore lint/a11y/noNoninteractiveTabindex: the explanation opens when the text has the focus (a keyboard has no hover)
      tabIndex={0}
      onPointerEnter={(e) => e.pointerType === "mouse" && setOpen(true)}
      onPointerLeave={(e) => {
        if (e.pointerType === "mouse") setOpen(false);
        else clearPress();
      }}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onPointerDown={(e) => {
        if (e.pointerType === "mouse") return;
        clearPress();
        press.current = setTimeout(() => {
          setOpen(true);
          if (stay.current !== null) clearTimeout(stay.current);
          stay.current = setTimeout(() => setOpen(false), STAY_MS);
        }, PRESS_MS);
      }}
      onPointerUp={clearPress}
      onPointerCancel={clearPress}
      onContextMenu={(e) => e.preventDefault()}
      style={{ WebkitTouchCallout: "none", userSelect: "none" }}
    >
      {children}
      {open ? (
        <span className="helptip-box" role="tooltip">
          {tip}
        </span>
      ) : null}
    </span>
  );
}
