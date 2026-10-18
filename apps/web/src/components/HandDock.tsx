"use client";
// The player's hand (the open missions are on the player board) as a floating panel in the bottom left corner. It can be folded down to a tab so that more of the
// board shows; whether it is folded is remembered in this browser.
import { cardName } from "@/lib/moves";
import { isPhone, useBottomSpace, useDock } from "@/lib/useDock";
import type { View } from "@seti/protocol";
import { useRef, useState } from "react";
import { useEffect, useRef as useRefHook } from "react";
import expansionAssets from "../generated/expansion-assets.json";
import { type CardAction, CardActions } from "./CardActions";
import { CardImage } from "./CardImage";
import { MascamiteTab } from "./Mascamites";

const SECURITY_BACKS: Record<string, string> = Object.fromEntries(
  ["pink", "yellow", "blue"].map((c) => [c, (expansionAssets as Record<string, string>)[`arkhos/security-back-${c}`] ?? ""]),
);

/** The cards of the hand that a move can be made with, the places (in the hand) of those that are picked, and what happens when one is clicked. */
export interface HandSelection {
  selectable: string[];
  selected: number[];
  onSelect: (index: number) => void;
  /** The game waits for a card of the hand (a tuck for income, a discard ...): the hand opens by itself, which matters on a phone where it starts folded. */
  autoOpen?: boolean;
  /** What can be done with the card that is picked, when it is the only one: buttons laid over it. */
  actions?: CardAction[];
  /** Cards that are offered to the player to keep one of (the end-of-round cards after passing): they lie with the hand for the moment. */
  offered?: string[];
  offeredSelected?: string | null;
  onOffer?: (card: string) => void;
}

/** The tab with the player's Exertian cards (ALIEN-EXE-01 to ALIEN-EXE-07): those still held, those played face down, and the milestones. */
export function ExertianTab({ view }: { view: View }) {
  const me = view.viewer;
  const player = me === null ? undefined : view.state.players[me];
  const slot = view.state.species.find((sp) => sp.discovered && sp.species === "exertians");
  if (!player || !slot) return null;
  const tracker = view.trackers?.[player.index];
  const milestones = (slot.extra.milestones ?? []) as { at: number; cost: number; done: number[] }[];
  return (
    <div className="exertiantab">
      <div className="cards">
        <b className="offerlabel">Available ({player.exertian_hand.length})</b>
        {player.exertian_hand.length === 0 ? <span className="muted">No Exertian cards left to play.</span> : null}
        {player.exertian_hand.map((c, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: ids are unique, the index only guards a hidden card
          <CardImage key={`${c}-${i}`} id={c} size="hand" />
        ))}
        <span className="handsep" aria-hidden="true" />
        <b className="offerlabel">Played face down ({player.exertian_played.length})</b>
        {player.exertian_played.length === 0 ? <span className="muted">None played yet.</span> : null}
        {player.exertian_played.map((c, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: ids are unique, the index only guards a hidden card
          <CardImage key={`${c}-${i}`} id={c} size="hand" />
        ))}
      </div>
      <p className="muted">
        Danger: {tracker?.danger_cards ?? 0} from played cards + {tracker?.danger_board ?? 0} from the species board ={" "}
        <b>{(tracker?.danger_cards ?? 0) + (tracker?.danger_board ?? 0)}</b>. Milestones:{" "}
        {milestones
          .map(
            (m, i) =>
              `${i + 1}: ${m.at} points, ${m.cost > 0 ? `${m.cost} credit` : "free"}${m.done.includes(player.index) ? " (crossed)" : ""}`,
          )
          .join("; ")}
        .
      </p>
    </div>
  );
}

export function HandDock({ view, selection }: { view: View; selection?: HandSelection }) {
  const [folded, toggle, set] = useDock("hand");
  const wanted = (selection?.offered?.length ?? 0) > 0 || selection?.autoOpen === true;
  const wasWanted = useRefHook(false);
  // the hand opens by itself when cards are offered, so that the player sees them
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when cards become offered
  useEffect(() => {
    if (wanted && !wasWanted.current) set(true);
    wasWanted.current = wanted;
  }, [wanted]);
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "hand");
  const me = view.viewer;
  const player = me === null ? undefined : view.state.players[me];
  const [tab, setTab] = useState<"hand" | "exertian" | "mascamite" | "security">("hand");
  if (!player) return null;
  // on a phone the Exertian cards have a tab of the bottom bar of their own (ExertianDock)
  const exertians = view.state.species.some((sp) => sp.discovered && sp.species === "exertians") && !isPhone();
  const mascamites = view.state.species.some((sp) => sp.discovered && sp.species === "mascamites");
  // Arkhos: the security cards lie in front of the player, apart from the hand; a breached card goes from this tab into the hand
  const arkhos = view.state.species.some((sp) => sp.discovered && sp.species === "arkhos");
  const security = Object.entries((player.security ?? {}) as Record<string, string>);
  const showSecurity = arkhos && tab === "security";
  const showExertian = exertians && tab === "exertian";
  const showMascamite = mascamites && tab === "mascamite";
  const who = (seat: number): string =>
    view.state.rival && seat === view.state.rival.index ? "Rival" : seat === view.viewer ? "You" : `Player ${seat + 1}`;
  return (
    <aside ref={dock} className={folded ? "hand dock folded" : "hand dock"} aria-label="Your hand">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Hand ({player.hand.length + (selection?.offered?.length ?? 0)})</span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <div className="handbody">
          {exertians || mascamites || arkhos ? (
            <div className="handtabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={!showExertian && !showMascamite && !showSecurity}
                onClick={() => setTab("hand")}
              >
                Hand
              </button>
              {exertians ? (
                <button type="button" role="tab" aria-selected={showExertian} onClick={() => setTab("exertian")}>
                  Exertian cards ({player.exertian_hand.length} held · {player.exertian_played.length} played)
                </button>
              ) : null}
              {mascamites ? (
                <button type="button" role="tab" aria-selected={showMascamite} onClick={() => setTab("mascamite")}>
                  Mascamite samples
                </button>
              ) : null}
              {arkhos ? (
                <button type="button" role="tab" aria-selected={showSecurity} onClick={() => setTab("security")}>
                  Security cards ({security.length})
                </button>
              ) : null}
            </div>
          ) : null}
          {showExertian ? <ExertianTab view={view} /> : null}
          {showMascamite ? <MascamiteTab view={view} who={who} /> : null}
          {showSecurity ? (
            <div className="cards">
              {security.length === 0 ? <span className="muted">All your security cards are breached: they are in your hand.</span> : null}
              {security.map(([color]) => (
                // only the back is shown until the card is breached: it shows the color of the trace that breaches it
                <span
                  key={color}
                  className="cardslot"
                  title={`${color} security card: breach it by marking the overflow space of that color`}
                >
                  <img
                    className="cardimg card-hand"
                    src={SECURITY_BACKS[color]}
                    alt={`${color} security card (face down until it is breached)`}
                  />
                </span>
              ))}
            </div>
          ) : null}
          <div className="cards" hidden={showExertian || showMascamite || showSecurity}>
            {player.hand.length === 0 ? <span className="muted">No cards in hand.</span> : null}
            {player.hand.map((c, i) => {
              const picked = selection?.selected.includes(i) ?? false;
              if (!selection?.selectable.includes(c)) {
                return (
                  <span
                    // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
                    key={`${c}-${i}`}
                    className={wanted || (selection && selection.selectable.length > 0) ? "cardslot dim" : "cardslot"}
                  >
                    <CardImage id={c} size="hand" />
                  </span>
                );
              }
              return (
                // biome-ignore lint/suspicious/noArrayIndexKey: the same card can be in hand twice
                <span key={`${c}-${i}`} className="cardwrap">
                  <button
                    type="button"
                    className={picked ? "cardbtn selectable selected" : "cardbtn selectable"}
                    aria-pressed={picked}
                    onClick={() => selection.onSelect(i)}
                  >
                    <CardImage id={c} size="hand" />
                  </button>
                  {picked && selection.selected.length === 1 && selection.actions ? <CardActions actions={selection.actions} /> : null}
                </span>
              );
            })}
            {(selection?.offered?.length ?? 0) > 0 ? (
              <>
                <span className="handsep offersep" aria-hidden="true" />
                <span className="offerbox">
                  <b className="offerlabel">Keep one of these</b>
                  <span className="offercards">
                    {selection?.offered?.map((c) => (
                      <button
                        key={c}
                        type="button"
                        className={selection.offeredSelected === c ? "cardbtn selectable selected" : "cardbtn selectable"}
                        aria-pressed={selection.offeredSelected === c}
                        onClick={() => selection.onOffer?.(c)}
                      >
                        <CardImage id={c} size="hand" />
                      </button>
                    ))}
                  </span>
                </span>
              </>
            ) : null}
            {player.kept_cards.length > 0 || player.message_cards.length > 0 ? <span className="handsep" aria-hidden="true" /> : null}
            {player.kept_cards.map((c) => (
              <CardImage key={c} id={c} size="mission" title={`${cardName(c)}: kept in front of you`} />
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

/** On a phone: the Exertian cards held and played are a tab of the bottom bar of their own, beside the hand. */
export function ExertianDock({ view }: { view: View }) {
  const [folded, toggle] = useDock("exertian");
  const player = view.viewer === null ? undefined : view.state.players[view.viewer];
  const has = view.state.species.some((sp) => sp.discovered && sp.species === "exertians");
  if (!player || !has) return null;
  return (
    <aside className={folded ? "exertdock dock folded" : "exertdock dock"} aria-label="Your Exertian cards">
      <button type="button" className="handtab" onClick={toggle} aria-expanded={!folded}>
        <span>Exertians ({player.exertian_hand.length})</span>
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {folded ? null : (
        <div className="handbody">
          <ExertianTab view={view} />
        </div>
      )}
    </aside>
  );
}
