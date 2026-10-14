"use client";
// The card row (the display) and the deck as a panel floating at the left edge, so that the board can use the width. It can be folded to a tab; it
// opens by itself when a card of the row can be clicked (to buy it, or to take it in a trade).
import { useDock } from "@/lib/useDock";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import { CardImage } from "./CardImage";

/** Picking a card of the card row (or the deck): which can be picked, which is, and what happens on a click. The sources are the engine's: "deck" and "row:<place>". */
export interface RowSelection {
  selectable: string[];
  selected: string | null;
  onSelect: (source: string) => void;
}

export function RowDock({ view, row }: { view: View; row?: RowSelection }) {
  const [folded, toggle, set] = useDock("row", () => window.innerWidth < 1700);
  const s = view.state;
  const wanted = (row?.selectable.length ?? 0) > 0;
  const shut = folded && !wanted;
  return (
    <aside className={shut ? "rowdock dock folded" : "rowdock dock"} aria-label="Card row">
      <button type="button" className="handtab" onClick={() => (wanted && folded ? set(true) : toggle())} aria-expanded={!shut}>
        <span>
          Card row{" "}
          <span className="muted small">
            deck {view.counts.deck} · discard {s.discard.length}
          </span>
        </span>
        <span aria-hidden="true">{shut ? "▸" : "◂"}</span>
      </button>
      {shut ? null : (
        <div className="rowbody">
          <div className="cards">
            {s.card_row.length === 0 ? <span className="muted">empty</span> : null}
            {s.card_row.map((c, i) => {
              const source = `row:${i}`;
              if (!row?.selectable.includes(source)) {
                // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                return <CardImage key={`${c}-${i}`} id={c} size="row" />;
              }
              return (
                <button
                  // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                  key={`${c}-${i}`}
                  type="button"
                  className={row.selected === source ? "cardbtn selectable selected" : "cardbtn selectable"}
                  aria-pressed={row.selected === source}
                  onClick={() => row.onSelect(source)}
                >
                  <CardImage id={c} size="row" />
                </button>
              );
            })}
            {row?.selectable.includes("deck") ? (
              <button
                type="button"
                className={row.selected === "deck" ? "cardbtn selectable selected deckbtn" : "cardbtn selectable deckbtn"}
                aria-pressed={row.selected === "deck"}
                onClick={() => row.onSelect("deck")}
                title="The top card of the deck"
              >
                <img src={assets.cardBack} alt="Top of the deck" width={300} height={418} className="cardimg decktile" />
                <span className="decklabel">Deck {view.counts.deck}</span>
              </button>
            ) : null}
          </div>
        </div>
      )}
    </aside>
  );
}
