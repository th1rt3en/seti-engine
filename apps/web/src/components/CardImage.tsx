"use client";
import { cardImage } from "@/lib/cardImages";
// A card image (generated/assets.json). A hidden card ("?") is shown as a card back. The files are WebP images with the hash of their content
// in the name, so Cloudflare and the browser keep them for good. Hovering a card shows it large beside it.
import { cardName } from "@/lib/moves";
import { ZOOM_SECONDS, touchScreen, useLongPress } from "@/lib/touch";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
/** Sent on the window when the pointer is on a card (the id) and when it leaves (null): the board outlines the planets and sectors the card names. */
export const CARD_HOVER_EVENT = "seti-card-hover";
/** The enlarged card is a quarter of the window wide, between these. */
const zoomWidth = (): number => Math.round(Math.min(500, Math.max(320, window.innerWidth * 0.26)));
const RATIO = 1040 / 747;
/** The enlarged card appears when the pointer has rested on a card this long. */
const HOVER_DELAY_MS = 1000;
/** The finger that held a card lifts over the enlarged card: that click must not close it at once. */
const RELEASE_GUARD_MS = 600;

/** Where the card is shown decides its size (CSS classes that follow the width of the window); `width` is used when no size is given. */
export type CardSize = "hand" | "mission" | "row";

export function CardImage({ id, width = 120, size, title }: { id: string; width?: number; size?: CardSize; title?: string }) {
  const [zoom, setZoom] = useState<{ x: number; y: number; w: number } | null>(null);
  const img = useRef<HTMLImageElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancel = () => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
    setZoom(null);
  };
  // on a touch screen the enlarged card goes away after a few seconds, or when it is tapped
  const opened = useRef(0);
  const showOnTouch = () => {
    cancel();
    show();
    opened.current = Date.now();
    timer.current = setTimeout(cancel, ZOOM_SECONDS * 1000);
  };
  useEffect(
    () => () => {
      if (timer.current !== null) clearTimeout(timer.current);
    },
    [],
  );
  const longPress = useLongPress(() => touchScreen() && showOnTouch());
  // the picture's own proportions (an organization is a landscape card, not a portrait one): known once it has loaded
  const [ratio, setRatio] = useState(RATIO);
  // a picture that has loaded before the page woke up does not tell its onLoad: read its size here too
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when the picture changes
  useEffect(() => {
    const el = img.current;
    if (el?.complete && el.naturalWidth > 0) setRatio(el.naturalHeight / el.naturalWidth);
  }, [id]);
  const height = Math.round(width * ratio);
  const src = cardImage(id);

  if (id === "?" || src === undefined) {
    return (
      <span
        className={size ? `cardback card-${size}` : "cardback"}
        style={size ? undefined : { width, height }}
        title={title ?? (id === "?" ? "hidden card" : id)}
      >
        {id === "?" ? "?" : id}
      </span>
    );
  }

  const show = () => {
    const r = img.current?.getBoundingClientRect();
    if (!r) return;
    // a landscape card is enlarged wider, so that it is as big on the screen as a portrait one
    const zw = Math.min(window.innerWidth - 16, ratio < 1 ? Math.round(zoomWidth() * 1.45) : zoomWidth());
    const zoomHeight = Math.round(zw * ratio);
    // beside the card, on the side with room; kept inside the window
    let x = r.right + 14;
    if (x + zw > window.innerWidth - 8) x = Math.max(8, r.left - zw - 14);
    const y = Math.min(Math.max(8, r.top + r.height / 2 - zoomHeight / 2), Math.max(8, window.innerHeight - zoomHeight - 8));
    setZoom({ x, y, w: zw });
  };

  return (
    <>
      <img
        {...longPress}
        ref={img}
        className={size ? `cardimg card-${size}` : "cardimg"}
        src={src}
        alt={cardName(id)}
        title={title ?? cardName(id)}
        width={size ? undefined : width}
        height={size ? undefined : height}
        loading="lazy"
        decoding="async"
        onLoad={(e) => {
          const { naturalWidth, naturalHeight } = e.currentTarget;
          if (naturalWidth > 0) setRatio(naturalHeight / naturalWidth);
        }}
        onMouseEnter={() => {
          if (touchScreen()) return; // a tap makes the browser fake a hover that would stay: touch has its own way (onClick)
          cancel();
          timer.current = setTimeout(show, HOVER_DELAY_MS);
          window.dispatchEvent(new CustomEvent(CARD_HOVER_EVENT, { detail: id })); // the board outlines the places the card names
        }}
        onMouseLeave={() => {
          if (touchScreen()) return;
          cancel();
          window.dispatchEvent(new CustomEvent(CARD_HOVER_EVENT, { detail: null }));
        }}
      />
      {zoom
        ? // in the page itself, so that no transform of the card or its panel moves it
          createPortal(
            // biome-ignore lint/a11y/useKeyWithClickEvents: a zoom of a picture for touch screens; the picture is not an action
            <img
              className="cardzoom"
              src={src}
              alt=""
              width={zoom.w}
              height={Math.round(zoom.w * ratio)}
              style={{ left: zoom.x, top: zoom.y, pointerEvents: touchScreen() ? "auto" : undefined }}
              onClick={() => Date.now() - opened.current > RELEASE_GUARD_MS && cancel()}
            />,
            document.body,
          )
        : null}
    </>
  );
}
