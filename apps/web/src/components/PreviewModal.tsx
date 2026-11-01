"use client";
// A panel over the page for the previews of the decks (the alien cards, the Arkhos exploration cards): it looks like the panel of the end-of-round
// cards (OfferPanel). A click beside it, the Close button or Escape puts it away.
import { type ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";

export function PreviewModal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (typeof document === "undefined") return null;
  return createPortal(
    <>
      <div className="overlay" onMouseDown={onClose} role="presentation" />
      {/* biome-ignore lint/a11y/useSemanticElements: a panel with its own backdrop, not a native <dialog> */}
      <section className="offerpanel previewpanel" role="dialog" aria-modal="true" aria-label={title}>
        <button type="button" className="offerhide secondary small" onClick={onClose}>
          Close ✕
        </button>
        <h2>{title}</h2>
        {children}
      </section>
    </>,
    document.body,
  );
}
