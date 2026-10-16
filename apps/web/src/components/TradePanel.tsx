"use client";
// The free trade (RES-06): one button in the move bar opens this panel. The player picks what to spend (2 credits, 2 energy or 2 cards of the hand) and
// what to get (1 credit, 1 energy or 1 card), then confirms. A card is then taken from the display or the deck: the panel closes and the page asks for that
// in the context bar. Every choice offered here is one of the engine's legal exchange moves; nothing is worked out here.
import type { Move } from "@/lib/moves";
import { useState } from "react";
import { CardImage } from "./CardImage";
import { CreditIcon, DeckCardIcon, EnergyIcon } from "./Icons";

const SPEND: { key: string; label: string; icon: React.ReactNode }[] = [
  { key: "credit", label: "2 credits", icon: <CreditIcon size={26} /> },
  { key: "energy", label: "2 energy", icon: <EnergyIcon size={26} /> },
  { key: "card", label: "2 cards from your hand", icon: <DeckCardIcon size={26} /> },
];
const GET: { key: string; label: string; icon: React.ReactNode }[] = [
  { key: "credit", label: "1 credit", icon: <CreditIcon size={26} /> },
  { key: "energy", label: "1 energy", icon: <EnergyIcon size={26} /> },
  { key: "card", label: "1 card (display or deck)", icon: <DeckCardIcon size={26} /> },
];

export function TradePanel({
  moves,
  hand,
  onPlay,
  onPickCard,
  onClose,
}: {
  /** All the exchange moves that are legal now. */
  moves: Move[];
  /** The cards of the player's hand, in order. */
  hand: string[];
  onPlay: (m: Move) => void;
  /** A card is wanted: the moves that take one (the page asks which, in the context bar). */
  onPickCard: (moves: Move[]) => void;
  onClose: () => void;
}) {
  const [spend, setSpend] = useState<string | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const [get, setGet] = useState<string | null>(null);
  const spendable = new Set(moves.map((m) => String(m.give)));
  const handCards = new Set(moves.filter((m) => m.give === "card").flatMap((m) => m.cards as string[]));
  const cards = picked.map((i) => hand[i]).filter((c): c is string => c !== undefined);
  // the moves that match what has been picked so far
  const matching = moves.filter(
    (m) =>
      m.give === spend &&
      (spend !== "card" || (cards.length === 2 && [...(m.cards as string[])].sort().join() === [...cards].sort().join())),
  );
  const gettable = new Set(matching.map((m) => String(m.get)));
  const ready = spend !== null && get !== null && gettable.has(get) && (spend !== "card" || cards.length === 2);
  const confirm = () => {
    if (!ready) return;
    const chosen = matching.filter((m) => m.get === get);
    onClose();
    if (get === "card") onPickCard(chosen);
    else if (chosen[0]) onPlay(chosen[0]);
  };
  const pickSpend = (key: string) => {
    setSpend(key);
    setPicked([]);
    setGet(null);
  };
  const toggleCard = (i: number) => {
    setGet(null);
    setPicked((old) => (old.includes(i) ? old.filter((x) => x !== i) : old.length >= 2 ? [old[1] as number, i] : [...old, i]));
  };
  return (
    <section className="tradepanel" aria-label="Trade resources">
      <header>
        <h2>Trade (free action)</h2>
        <button type="button" className="secondary" onClick={onClose} aria-label="Close the trade">
          ✕
        </button>
      </header>
      <p className="muted small">Trade 2 of one kind for 1 of any kind. You cannot mix two different resources.</p>
      <h3>Spend</h3>
      <div className="tradechoices">
        {SPEND.map((o) => (
          <button
            key={o.key}
            type="button"
            className={spend === o.key ? "tradeopt on" : "tradeopt"}
            aria-pressed={spend === o.key}
            disabled={!spendable.has(o.key)}
            title={spendable.has(o.key) ? undefined : "You cannot spend this now"}
            onClick={() => pickSpend(o.key)}
          >
            {o.icon} {o.label}
          </button>
        ))}
      </div>
      {spend === "card" ? (
        <>
          <p className="muted small">Pick the 2 cards to discard ({cards.length} of 2).</p>
          <div className="tradehand">
            {hand.map((c, i) =>
              handCards.has(c) ? (
                <button
                  // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
                  key={`${c}-${i}`}
                  type="button"
                  className={picked.includes(i) ? "cardbtn selectable selected" : "cardbtn selectable"}
                  aria-pressed={picked.includes(i)}
                  onClick={() => toggleCard(i)}
                >
                  <CardImage id={c} size="row" />
                </button>
              ) : null,
            )}
          </div>
        </>
      ) : null}
      <h3>Get</h3>
      <div className="tradechoices">
        {GET.map((o) => (
          <button
            key={o.key}
            type="button"
            className={get === o.key ? "tradeopt on" : "tradeopt"}
            aria-pressed={get === o.key}
            disabled={!gettable.has(o.key)}
            onClick={() => setGet(o.key)}
          >
            {o.icon} {o.label}
          </button>
        ))}
      </div>
      <footer>
        <button type="button" className="primary" disabled={!ready} onClick={confirm}>
          Confirm the trade
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
      </footer>
    </section>
  );
}
