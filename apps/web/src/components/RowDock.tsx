"use client";
// The card row (the display) and the deck as a panel floating at the left edge, so that the board can use the width. It can be folded to a tab; it
// opens by itself when a card of the row can be clicked (to buy it, or to take it in a trade).
import { isPhone, useDock } from "@/lib/useDock";
import type { View } from "@seti/protocol";
import { useEffect, useRef } from "react";
import assets from "../generated/assets.json";
import { type CardAction, CardActions } from "./CardActions";
import { CardImage } from "./CardImage";

/** Picking a card of the card row (or the deck): which can be picked, which is, and what happens on a click. The sources are the engine's: "deck" and "row:<place>". */
export interface RowSelection {
  selectable: string[];
  selected: string | null;
  onSelect: (source: string) => void;
  /** What can be done with the card that is picked: buttons laid over it (to confirm discarding it for a signal, for example). */
  actions?: CardAction[];
}

/** `inline`: on a wide screen the card row lies in the column of the tech stacks, below them, all cards in one row; the floating panel serves the narrow screens. */
export function RowDock({ view, row, inline, flash }: { view: View; row?: RowSelection; inline?: boolean; flash?: boolean }) {
  const [folded, toggle, set] = useDock("row", () => window.innerWidth < 1700);
  const s = view.state;
  const wanted = (row?.selectable.length ?? 0) > 0;
  const shut = inline ? false : folded;
  // the panel opens by itself when a card of it can be picked (to buy it, or to take it in a trade), and can be folded again at any time
  const wasWanted = useRef(false);
  const firstLook = useRef(true);
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when a card of the row becomes pickable
  useEffect(() => {
    // on a phone the page starts with the panels folded, whatever the game waits for
    if (wanted && !wasWanted.current && !(firstLook.current && isPhone())) set(true);
    wasWanted.current = wanted;
    firstLook.current = false;
  }, [wanted]);
  // when the row is to blink (a card is to be taken), bring it into view if it is out of it
  const box = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = box.current;
    if (flash && el && el.getBoundingClientRect().width > 0) el.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [flash]);
  return (
    <aside
      ref={box}
      className={`${inline ? "rowinline card" : shut ? "rowdock floating dock folded" : "rowdock floating dock"}${flash ? " flashing" : ""}`}
      aria-label="Card row"
    >
      {inline ? null : (
        <button type="button" className="handtab" onClick={toggle} aria-expanded={!shut}>
          <span>
            Card row{" "}
            <span className="muted small">
              deck {view.counts.deck} · discard {s.discard.length}
            </span>
          </span>
          <span aria-hidden="true">{shut ? "▸" : "◂"}</span>
        </button>
      )}
      {shut ? null : (
        <div className="rowbody">
          {inline ? (
            <h3 className="rowtitle">
              Card row{" "}
              <span className="muted small">
                deck {view.counts.deck} · discard {s.discard.length}
              </span>
            </h3>
          ) : null}
          <div className="cards">
            {s.card_row.length === 0 ? <span className="muted">empty</span> : null}
            {s.card_row.map((c, i) => {
              const source = `row:${i}`;
              if (!row?.selectable.includes(source)) {
                // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                return <CardImage key={`${c}-${i}`} id={c} size="row" />;
              }
              return (
                // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                <span key={`${c}-${i}`} className="cardwrap">
                  <button
                    type="button"
                    className={row.selected === source ? "cardbtn selectable selected" : "cardbtn selectable"}
                    aria-pressed={row.selected === source}
                    onClick={() => row.onSelect(source)}
                  >
                    <CardImage id={c} size="row" />
                  </button>
                  {row.selected === source && row.actions ? <CardActions actions={row.actions} /> : null}
                </span>
              );
            })}
            {row?.selectable.includes("deck") ? (
              <span className="cardwrap deckwrap">
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
                {row.selected === "deck" && row.actions ? <CardActions actions={row.actions} /> : null}
              </span>
            ) : null}
          </div>
        </div>
      )}
    </aside>
  );
}
