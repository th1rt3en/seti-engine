"use client";
// The name of an organization, wherever it is written: resting the pointer on it for a second shows the whole organization board beside it (on a touch
// screen a long press does, like the cards).
import { cardImage, orgNameImage } from "@/lib/cardImages";
import { ORG_NAMES } from "@/lib/moves";
import { ZOOM_SECONDS, touchScreen, useLongPress } from "@/lib/touch";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

const HOVER_DELAY_MS = 1000;
const RATIO = 421 / 560; // the organization boards are landscape pictures of 560 x 421
const zoomWidth = (): number => Math.round(Math.min(720, Math.max(320, window.innerWidth * 0.5)));

/** `banner` shows the printed name from the card (a picture, the same size for every organization) instead of the plain name. */
export function OrgName({ id, className, banner }: { id: string; className?: string; banner?: boolean }) {
  const [zoom, setZoom] = useState<{ x: number; y: number; w: number } | null>(null);
  const node = useRef<HTMLSpanElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
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
    const r = node.current?.getBoundingClientRect();
    if (!r) return;
    const w = Math.min(zoomWidth(), window.innerWidth - 16);
    const h = Math.round(w * RATIO);
    // under the name, or above it when there is no room; kept inside the window
    let y = r.bottom + 10;
    if (y + h > window.innerHeight - 8) y = Math.max(8, r.top - h - 10);
    const x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    setZoom({ x, y, w });
  };
  const longPress = useLongPress(() => {
    if (!touchScreen()) return;
    cancel();
    show();
    timer.current = setTimeout(cancel, ZOOM_SECONDS * 1000);
  });
  const src = cardImage(id);
  const bannerSrc = orgNameImage(id);
  return (
    <>
      <span
        {...longPress}
        ref={node}
        className={className}
        onMouseEnter={() => {
          if (touchScreen() || !src) return;
          cancel();
          timer.current = setTimeout(show, HOVER_DELAY_MS);
        }}
        onMouseLeave={() => !touchScreen() && cancel()}
      >
        {banner && bannerSrc ? (
          <img src={bannerSrc} alt={ORG_NAMES[id] ?? id} width={262} height={28} className="org-banner" />
        ) : (
          (ORG_NAMES[id] ?? id)
        )}
      </span>
      {zoom && src
        ? createPortal(
            // biome-ignore lint/a11y/useKeyWithClickEvents: a zoom of a picture for touch screens; the picture is not an action
            <img
              className="cardzoom"
              src={src}
              alt={ORG_NAMES[id] ?? id}
              width={zoom.w}
              height={Math.round(zoom.w * RATIO)}
              style={{ left: zoom.x, top: zoom.y, pointerEvents: touchScreen() ? "auto" : undefined }}
              onClick={cancel}
            />,
            document.body,
          )
        : null}
    </>
  );
}
