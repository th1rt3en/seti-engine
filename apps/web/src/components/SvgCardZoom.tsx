"use client";
// A card that is drawn inside an SVG (the face-up card of an alien species on the main board): resting the pointer on it for a second shows it large beside
// it, like the cards of the hand and of the row (CardImage); on a touch screen holding it does the same.
import { ZOOM_SECONDS, touchScreen, useLongPress } from "@/lib/touch";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CARD_HOVER_EVENT, HOVER_DELAY_MS, RATIO, zoomWidth } from "./CardImage";

export function SvgCardZoom({ id, src, ratio = RATIO, children }: { id: string | null; src: string; ratio?: number; children: ReactNode }) {
  const group = useRef<SVGGElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [zoom, setZoom] = useState<{ x: number; y: number; w: number } | null>(null);
  const cancel = () => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
    setZoom(null);
  };
  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );
  const show = () => {
    const r = group.current?.getBoundingClientRect();
    if (!r) return;
    const zw = Math.min(window.innerWidth - 16, zoomWidth());
    const zh = Math.round(zw * ratio);
    let x = r.right + 14;
    if (x + zw > window.innerWidth - 8) x = Math.max(8, r.left - zw - 14);
    const y = Math.min(Math.max(8, r.top + r.height / 2 - zh / 2), Math.max(8, window.innerHeight - zh - 8));
    setZoom({ x, y, w: zw });
  };
  const longPress = useLongPress(() => {
    if (!touchScreen()) return;
    cancel();
    show();
    timer.current = setTimeout(cancel, ZOOM_SECONDS * 1000);
  });
  return (
    <>
      <g
        {...longPress}
        ref={group}
        onMouseEnter={() => {
          if (touchScreen()) return;
          cancel();
          timer.current = setTimeout(show, HOVER_DELAY_MS);
          if (id !== null) window.dispatchEvent(new CustomEvent(CARD_HOVER_EVENT, { detail: id }));
        }}
        onMouseLeave={() => {
          if (touchScreen()) return;
          cancel();
          if (id !== null) window.dispatchEvent(new CustomEvent(CARD_HOVER_EVENT, { detail: null }));
        }}
      >
        {children}
      </g>
      {zoom
        ? createPortal(
            <img
              className="cardzoom"
              src={src}
              alt=""
              width={zoom.w}
              height={Math.round(zoom.w * ratio)}
              style={{ left: zoom.x, top: zoom.y }}
            />,
            document.body,
          )
        : null}
    </>
  );
}
