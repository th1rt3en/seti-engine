"use client";
// The cards that are offered to keep one of (the end-of-round cards after passing, PASS-04): a panel of their own, over the page, instead of lying with the
// hand. The player picks one card and keeps it; the cards that are not kept stay where they were.
import { CardImage } from "./CardImage";

export function OfferPanel({
  title,
  text,
  cards,
  selected,
  keepLabel,
  onSelect,
  onKeep,
}: {
  title: string;
  text: string;
  cards: string[];
  selected: string | null;
  keepLabel: string;
  onSelect: (card: string) => void;
  onKeep: () => void;
}) {
  return (
    <section className="offerpanel" aria-label={title}>
      <h2>{title}</h2>
      <p className="muted small">{text}</p>
      <div className="offercards">
        {cards.map((c) => (
          <button
            key={c}
            type="button"
            className={c === selected ? "offercard chosen" : "offercard"}
            aria-pressed={c === selected}
            onClick={() => onSelect(c)}
          >
            <CardImage id={c} width={150} />
          </button>
        ))}
      </div>
      <button type="button" className="primary" disabled={selected === null} onClick={onKeep}>
        {selected === null ? "Pick a card" : keepLabel}
      </button>
    </section>
  );
}
