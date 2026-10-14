"use client";
// A picture that can be enlarged. With a mouse the enlarged version appears beside it after a second of hovering (CSS, `.zoomable`); on a touch screen
// holding it for a second shows the picture large in the middle of the window (a tap does nothing), and it goes away by itself after a few seconds or when it is tapped.
import { ZOOM_SECONDS, touchScreen, useLongPress } from "@/lib/touch";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function TapZoomImage({
  src,
  alt,
  width,
  height,
  className,
  title,
}: { src: string; alt: string; width: number; height: number; className?: string; title?: string }) {
  const [open, setOpen] = useState(false);
  const openedAt = useRef(0);
  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => setOpen(false), ZOOM_SECONDS * 1000);
    return () => clearTimeout(timer);
  }, [open]);
  const longPress = useLongPress(() => {
    if (!touchScreen()) return;
    openedAt.current = Date.now();
    setOpen(true);
  });
  return (
    <>
      <img
        {...longPress}
        src={src}
        alt={alt}
        title={title}
        width={width}
        height={height}
        className={className}
        loading="lazy"
        decoding="async"
      />
      {open
        ? createPortal(
            // biome-ignore lint/a11y/useKeyWithClickEvents: it also goes away by itself after a few seconds
            <div className="tapzoom" onClick={() => Date.now() - openedAt.current > 600 && setOpen(false)}>
              <img src={src} alt={alt} />
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
