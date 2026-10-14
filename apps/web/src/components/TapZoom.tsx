"use client";
// A picture that can be enlarged. With a mouse the enlarged version appears beside it after a second of hovering (CSS, `.zoomable`); on a touch screen
// tapping it shows the picture large in the middle of the window, and it goes away by itself after a few seconds or when it is tapped.
import { ZOOM_SECONDS, touchScreen } from "@/lib/touch";
import { useEffect, useState } from "react";
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
  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(() => setOpen(false), ZOOM_SECONDS * 1000);
    return () => clearTimeout(timer);
  }, [open]);
  return (
    <>
      {/* biome-ignore lint/a11y/useKeyWithClickEvents: a zoom of a picture for touch screens; the picture is not an action */}
      <img
        src={src}
        alt={alt}
        title={title}
        width={width}
        height={height}
        className={className}
        loading="lazy"
        decoding="async"
        onClick={() => touchScreen() && setOpen(true)}
      />
      {open
        ? createPortal(
            // biome-ignore lint/a11y/useKeyWithClickEvents: it also goes away by itself after a few seconds
            <div className="tapzoom" onClick={() => setOpen(false)}>
              <img src={src} alt={alt} />
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
