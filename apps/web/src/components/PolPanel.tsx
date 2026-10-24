"use client";
// #ET.15 Part of Everyday Life (FAQ-C215): the cards drawn by the card, in a panel. The player discards one for its free-action corner, then another for its
// income resource, and keeps the third. Only the player sees the drawn cards (the engine projects them); the log names each card that is discarded.
import { cornerWords, incomeWords } from "@/lib/moves";
import type { Move } from "@/lib/moves";
import { CardImage } from "./CardImage";

export function PolPanel({
  step,
  cards,
  moves,
  discarded,
  onPick,
}: {
  step: "corner" | "income";
  /** The cards still lying there. */
  cards: string[];
  moves: Move[];
  /** The card that was discarded for its free action, in the second step. */
  discarded: string | null;
  onPick: (m: Move) => void;
}) {
  const of = (c: string) => moves.find((m) => m.type === "pol_pick" && m.card === c);
  return (
    <div className="polpanel" aria-label="The cards drawn by Part of Everyday Life">
      <div className="small">
        <b>Part of Everyday Life</b> · step {step === "corner" ? 1 : 2} of 2.{" "}
        {step === "corner"
          ? "The card you pick is discarded and you gain its free-action corner (top left of the card)."
          : "The card you pick is discarded and you gain 1 of its income resource (the symbol at the bottom right of the card). The last card goes to your hand."}
      </div>
      <div className="polcards">
        {discarded ? (
          <div className="polcard gone">
            <CardImage id={discarded} width={110} />
            <span className="muted small">discarded for its free action</span>
          </div>
        ) : null}
        {cards.map((c) => {
          const m = of(c);
          return (
            <div key={c} className="polcard">
              <CardImage id={c} width={110} />
              {m ? (
                <button type="button" className="primary small" onClick={() => onPick(m)}>
                  {step === "corner" ? `Discard for its free action: ${cornerWords(c)}` : `Discard for its income: ${incomeWords(c)}`}
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
