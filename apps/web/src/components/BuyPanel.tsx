"use client";
// Buying a card for publicity (a free action): one button in the move bar opens this panel. The three cards of the display (and the top of the deck, when
// the engine allows it) are shown; the player picks one and confirms. The engine refills the slot of the card that was taken at once. Every choice is one of
// the engine's legal `buy_card` moves; nothing is worked out here.
import type { Move } from "@/lib/moves";
import { useState } from "react";
import assets from "../generated/assets.json";
import { CardImage } from "./CardImage";
import { PublicityIcon } from "./Icons";

export function BuyPanel({
  moves,
  row,
  deck,
  price,
  onBuy,
  onClose,
}: {
  /** The legal buy moves now: each has a `source`, "row:<place>" or "deck". */
  moves: Move[];
  /** The cards of the display, by place. */
  row: string[];
  /** How many cards the deck holds. */
  deck: number;
  /** The publicity that the card costs (the engine's note of the move). */
  price: number;
  onBuy: (m: Move) => void;
  onClose: () => void;
}) {
  const [picked, setPicked] = useState<string | null>(null);
  const bySource = new Map(moves.map((m) => [String(m.source), m]));
  const chosen = picked === null ? undefined : bySource.get(picked);
  return (
    <section className="tradepanel buypanel" aria-label="Take a card for publicity">
      <header>
        <h2>
          Lose {price} <PublicityIcon size={22} /> to take a card
        </h2>
        <button type="button" className="secondary" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <p className="muted small">Free action. Pick a card of the display: its place is filled again at once.</p>
      <div className="buychoices">
        {row.map((id, i) => {
          const source = `row:${i}`;
          const ok = bySource.has(source);
          return (
            <button
              // biome-ignore lint/suspicious/noArrayIndexKey: the place is the identity of a card of the display
              key={`${id}-${i}`}
              type="button"
              className={picked === source ? "buychoice selected" : "buychoice"}
              aria-pressed={picked === source}
              disabled={!ok}
              onClick={() => setPicked(picked === source ? null : source)}
            >
              <CardImage id={id} width={150} />
            </button>
          );
        })}
        {bySource.has("deck") ? (
          <button
            type="button"
            className={picked === "deck" ? "buychoice selected" : "buychoice"}
            aria-pressed={picked === "deck"}
            onClick={() => setPicked(picked === "deck" ? null : "deck")}
            title="The top card of the deck"
          >
            <img src={assets.cardBack} alt="The top card of the deck" width={150} className="cardimg" />
            <span className="muted small">Deck ({deck})</span>
          </button>
        ) : null}
      </div>
      <div className="tradeactions">
        <button
          type="button"
          className="primary"
          disabled={chosen === undefined}
          onClick={() => {
            if (!chosen) return;
            onClose();
            onBuy(chosen);
          }}
        >
          Take the card
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
      </div>
    </section>
  );
}
