"use client";
// The preview of the rival's unused action cards (the cards that it has not played this round): a panel that opens when the deck in the rival's zone or the
// card counter of the rival's pill is clicked. The engine sends the cards by card number, not in the order of the deck, and an advanced card that the rival has
// not played yet is only a back (the basic cards and the species cards are known). Nothing is worked out here.
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import { rivalCardImage } from "./SoloPanel";
import { TapZoomImage } from "./TapZoom";

/** Sent on the window to open the panel. */
export const RIVAL_DECK_EVENT = "seti-rival-deck";
export const openRivalDeck = (): boolean => window.dispatchEvent(new CustomEvent(RIVAL_DECK_EVENT));

export function RivalDeckPanel({ view }: { view: View }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener(RIVAL_DECK_EVENT, show);
    return () => window.removeEventListener(RIVAL_DECK_EVENT, show);
  }, []);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);
  const rival = view.state.rival;
  if (!open || !rival) return null;
  const known = rival.deck.filter((c) => c !== "?");
  const unknown = rival.deck.length - known.length;
  return (
    <section className="offerpanel rivaldeckpanel" aria-label="The rival's unused action cards">
      <h2>
        The rival's unused action cards <span className="muted small">{rival.deck.length}</span>
      </h2>
      <p className="muted small">
        The cards it has not played this round, in the order of their numbers (not the order of the deck).
        {unknown > 0
          ? ` ${unknown} advanced card${unknown === 1 ? " is" : "s are"} shown as a back: you have not seen ${unknown === 1 ? "it" : "them"} yet.`
          : ""}
      </p>
      <div className="offercards">
        {rival.deck.length === 0 ? <span className="muted">No card is left: the rival passes.</span> : null}
        {rival.deck.map((id, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: the unseen cards are all alike; the order of the list is the identity
          <figure
            key={`${id}-${i}`}
            className="rcard"
            title={id === "?" ? "An advanced action card that has not been played yet" : `Card ${id}`}
          >
            <TapZoomImage
              src={id === "?" ? rivalCardImage("back") : rivalCardImage(id)}
              alt={id === "?" ? "An advanced action card (back)" : `Rival action card ${id}`}
              width={330}
              height={367}
            />
            <figcaption>{id === "?" ? "?" : id}</figcaption>
          </figure>
        ))}
      </div>
      <button type="button" className="secondary" onClick={() => setOpen(false)}>
        Close
      </button>
    </section>
  );
}
