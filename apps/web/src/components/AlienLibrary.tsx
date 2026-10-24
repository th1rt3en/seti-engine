"use client";
// The alien tab of the library: a tile for each species; a click opens a panel with every card of that species, in labelled sections when a species has
// more than one kind of card (Arkhos: the alien cards, the exploration cards and the security cards). It shows what the engine's data lists; it works out
// no rule.
import { useEffect, useRef, useState } from "react";
import { CardImage } from "./CardImage";

export interface AlienCards {
  /** The name of the section: "Alien cards", "Exploration cards" ... */
  label: string;
  /** What the section is, in a sentence. */
  note?: string;
  cards: { id: string; caption?: string }[];
}

export interface AlienTile {
  key: string;
  name: string;
  src: string | undefined;
  expansion?: boolean;
  sections: AlienCards[];
}

export function AlienLibrary({ aliens }: { aliens: AlienTile[] }) {
  const [open, setOpen] = useState<string | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const alien = aliens.find((a) => a.key === open) ?? null;
  useEffect(() => {
    if (alien === null) return;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [alien]);
  const total = alien?.sections.reduce((n, s) => n + s.cards.length, 0) ?? 0;
  return (
    <>
      <div className="libgrid aliens">
        {aliens.map((a) => (
          <figure key={a.key}>
            <button
              type="button"
              className="alienpick"
              onClick={() => setOpen(a.key)}
              aria-haspopup="dialog"
              title={`Show the cards of ${a.name}`}
              style={{ all: "unset", cursor: "pointer", display: "block" }}
            >
              <img src={a.src} alt={`${a.name} board`} loading="lazy" />
            </button>
            <figcaption>
              <b>{a.name}</b>
              {a.expansion ? <span className="muted small">Space Agencies</span> : null}
              <span className="muted small">{a.sections.reduce((n, s) => n + s.cards.length, 0)} cards: click to see them</span>
            </figcaption>
          </figure>
        ))}
      </div>
      {alien ? (
        // biome-ignore lint/a11y/useKeyWithClickEvents: the backdrop closes the panel with the mouse; the keyboard has Escape and the Close button
        <div className="alienbackdrop" onClick={(e) => e.target === e.currentTarget && setOpen(null)}>
          <div
            ref={panel}
            className="alienpanel"
            // biome-ignore lint/a11y/useSemanticElements: a layer that the page controls itself, not a native <dialog>
            role="dialog"
            aria-modal="true"
            aria-label={`The cards of ${alien.name}`}
            tabIndex={-1}
          >
            <header className="alienpanelhead">
              <h2>
                {alien.name} <span className="muted small">{total} cards</span>
              </h2>
              <button type="button" className="secondary small" onClick={() => setOpen(null)}>
                Close
              </button>
            </header>
            {alien.sections.map((s) => (
              <section key={s.label} aria-label={s.label}>
                <h3>
                  {s.label} <span className="muted small">{s.cards.length}</span>
                </h3>
                {s.note ? <p className="muted small">{s.note}</p> : null}
                <div className="alienpanelcards">
                  {s.cards.map((c) => (
                    <figure key={c.id}>
                      <CardImage id={c.id} width={150} />
                      <figcaption className="muted small">{c.caption ?? c.id}</figcaption>
                    </figure>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
