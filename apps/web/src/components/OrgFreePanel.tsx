"use client";
// A free action of an organization that is made with a card of the hand (Helion Assembly, Deep Sky Survey, Futurespan Institute). The card actions of the
// hand already offer it, but a phone keeps the hand folded: this panel is opened by a button in the move bar. The player picks the tech to destroy, the card of the
// hand and the card of the display where the move has them, and confirms. Every combination offered is one of the engine's legal moves.
import { type Move, describeMove, orgName } from "@/lib/moves";
import { useState } from "react";
import { CardImage } from "./CardImage";

export function OrgFreePanel({
  moves,
  hand,
  onPlay,
  onClose,
}: {
  /** The legal `org_free` moves that name a card of the hand. */
  moves: Move[];
  hand: string[];
  onPlay: (m: Move) => void;
  onClose: () => void;
}) {
  const org = String(moves[0]?.org ?? "");
  const techs = [...new Set(moves.map((m) => m.tech).filter((t): t is string => typeof t === "string"))];
  const rows = [...new Set(moves.map((m) => m.row).filter((r): r is number => typeof r === "number"))];
  const [tech, setTech] = useState<string | null>(techs.length === 1 ? (techs[0] ?? null) : null);
  const [row, setRow] = useState<number | null>(rows.length === 1 ? (rows[0] ?? null) : null);
  const [card, setCard] = useState<number | null>(null);
  const cardId = card === null ? undefined : hand[card];
  const match = moves.find(
    (m) => cardId !== undefined && m.card === cardId && (techs.length === 0 || m.tech === tech) && (rows.length === 0 || m.row === row),
  );
  const usable = new Set(moves.map((m) => String(m.card)));
  return (
    <section className="tradepanel" aria-label={`${orgName(org)} free action`}>
      <header>
        <h2>{orgName(org)}: free action</h2>
        <button type="button" className="secondary" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      {techs.length > 0 ? (
        <>
          <h3>Tech to destroy</h3>
          <div className="tradechoices">
            {techs.map((t) => (
              <button
                key={t}
                type="button"
                className={tech === t ? "tradeopt on" : "tradeopt"}
                aria-pressed={tech === t}
                onClick={() => setTech(t)}
              >
                {t.replace("-", " ")}
              </button>
            ))}
          </div>
        </>
      ) : null}
      {rows.length > 0 ? (
        <>
          <h3>Card of the display to switch with</h3>
          <div className="tradechoices">
            {rows.map((r) => (
              <button
                key={r}
                type="button"
                className={row === r ? "tradeopt on" : "tradeopt"}
                aria-pressed={row === r}
                onClick={() => setRow(r)}
              >
                Card {r + 1} of the display
              </button>
            ))}
          </div>
        </>
      ) : null}
      <h3>Card of your hand</h3>
      <div className="tradehand">
        {hand.map((c, i) =>
          usable.has(c) ? (
            <button
              // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
              key={`${c}-${i}`}
              type="button"
              className={card === i ? "cardbtn selectable selected" : "cardbtn selectable"}
              aria-pressed={card === i}
              onClick={() => setCard(i)}
            >
              <CardImage id={c} size="row" />
            </button>
          ) : null,
        )}
      </div>
      {match ? <p className="muted small">{describeMove(match)}</p> : null}
      <footer>
        <button
          type="button"
          className="primary"
          disabled={!match}
          onClick={() => {
            if (match) {
              onClose();
              onPlay(match);
            }
          }}
        >
          Confirm
        </button>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
      </footer>
    </section>
  );
}
