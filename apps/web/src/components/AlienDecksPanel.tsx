"use client";
// The preview of the alien decks: a click on the deck of a species (or its button here) opens a panel over the page, like the one of the end-of-round
// cards, with the cards of that species that the player cannot account for yet, the ones in their own hand, and the ones that have been revealed. An
// opponent's card that is played in the open moves from the first group to the last. The Exertian deck is empty after the deal (ALIEN-EXE-02), and
// its preview is the way to check what the opponents may hold.
import { ALIEN_PREVIEW_EVENT, deckPreview, speciesCards } from "@/lib/alienDecks";
import type { View } from "@seti/protocol";
import { useCallback, useEffect, useState } from "react";
import { CardImage } from "./CardImage";
import { PreviewModal } from "./PreviewModal";

const title = (species: string): string => species.charAt(0).toUpperCase() + species.slice(1);

function Cards({ ids, what }: { ids: string[]; what: string }) {
  return (
    <div className="aliencards offercards" aria-label={what}>
      {ids.map((id) => (
        <CardImage key={id} id={id} size="row" />
      ))}
    </div>
  );
}

export function AlienDecksPanel({ view }: { view: View }) {
  const [open, setOpen] = useState<string | null>(null);
  const close = useCallback(() => setOpen(null), []);
  useEffect(() => {
    const on = (e: Event) => setOpen(String((e as CustomEvent<string>).detail));
    window.addEventListener(ALIEN_PREVIEW_EVENT, on);
    return () => window.removeEventListener(ALIEN_PREVIEW_EVENT, on);
  }, []);
  const species = view.state.species.filter((sp) => sp.discovered && speciesCards(sp.species).length > 0);
  if (species.length === 0) return null;
  const shown = open !== null && species.some((sp) => sp.species === open) ? open : null;
  const preview = shown === null ? null : deckPreview(view, shown);
  const slot = species.find((sp) => sp.species === shown);
  return (
    <section className="card exppanel" aria-label="Alien decks">
      <h3>Alien cards</h3>
      <p className="small muted">
        {species.map((sp) => (
          <button key={sp.species} type="button" className="link" onClick={() => setOpen(sp.species)}>
            Look at the {title(sp.species)} cards
          </button>
        ))}
      </p>
      {preview !== null && shown !== null ? (
        <PreviewModal title={`${title(shown)} cards`} onClose={close}>
          <p className="small muted">
            {slot?.deck.length ?? 0} cards in the deck.{" "}
            {shown === "exertians"
              ? "The cards were dealt to the players when the species was discovered, and the ones that are played lie face down: any card you cannot see could be in an opponent's hand or played."
              : "The deck and the hands of the opponents are secret: any card you have not seen could be in the deck or in an opponent's hand."}
          </p>
          <h3>Could still be hidden ({preview.possible.length})</h3>
          {preview.possible.length > 0 ? (
            <Cards ids={preview.possible} what="Could still be hidden" />
          ) : (
            <p className="small muted">None.</p>
          )}
          {preview.yours.length > 0 ? (
            <>
              <h3>In your hand ({preview.yours.length})</h3>
              <Cards ids={preview.yours} what="In your hand" />
            </>
          ) : null}
          <h3>Revealed ({preview.revealed.length})</h3>
          {preview.revealed.length > 0 ? (
            <Cards ids={preview.revealed} what="Revealed" />
          ) : (
            <p className="small muted">No card of this species is in the open.</p>
          )}
        </PreviewModal>
      ) : null}
    </section>
  );
}
