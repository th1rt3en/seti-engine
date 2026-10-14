"use client";
// The player's hand and open missions as a floating panel in the bottom left corner. It can be folded down to a tab so that more of the
// board shows; whether it is folded is remembered in this browser.
import { cardName } from "@/lib/moves";
import { useBottomSpace, useDock } from "@/lib/useDock";
import type { View } from "@seti/protocol";
import { useRef } from "react";
import { CardImage } from "./CardImage";

/** The cards of the hand that a move can be made with, the places (in the hand) of those that are picked, and what happens when one is clicked. */
export interface HandSelection {
  selectable: string[];
  selected: number[];
  onSelect: (index: number) => void;
}

export function HandDock({ view, selection }: { view: View; selection?: HandSelection }) {
  const [folded, toggle] = useDock("hand");
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "hand");
  const me = view.viewer;
  const player = me === null ? undefined : view.state.players[me];
  if (!player) return null;
  return (
    <aside ref={dock} className={folded ? "hand dock folded" : "hand dock"} aria-label="Your hand">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>
          Hand ({player.hand.length}){player.missions.length > 0 ? ` · ${player.missions.length} missions` : ""}
        </span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <div className="handbody">
          <div className="cards">
            {player.hand.length === 0 ? <span className="muted">No cards in hand.</span> : null}
            {player.hand.map((c, i) => {
              const picked = selection?.selected.includes(i) ?? false;
              if (!selection?.selectable.includes(c)) {
                return (
                  // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
                  <span key={`${c}-${i}`} className={selection && selection.selectable.length > 0 ? "cardslot dim" : "cardslot"}>
                    <CardImage id={c} size="hand" />
                  </span>
                );
              }
              return (
                <button
                  // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
                  key={`${c}-${i}`}
                  type="button"
                  className={picked ? "cardbtn selectable selected" : "cardbtn selectable"}
                  aria-pressed={picked}
                  onClick={() => selection.onSelect(i)}
                >
                  <CardImage id={c} size="hand" />
                </button>
              );
            })}
            {player.missions.length > 0 ? <span className="handsep" aria-hidden="true" /> : null}
            {player.missions.map((m) => (
              <CardImage
                key={m.card}
                id={m.card}
                size="mission"
                title={`Open mission ${cardName(m.card)}: ${m.kind === "trigger" ? `${m.used.filter(Boolean).length}/${m.used.length} circles` : "quick mission"}`}
              />
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
