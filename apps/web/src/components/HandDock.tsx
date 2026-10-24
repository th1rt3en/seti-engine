"use client";
// The player's hand (the open missions are on the player board) as a floating panel in the bottom left corner. It can be folded down to a tab so that more of the
// board shows; whether it is folded is remembered in this browser.
import { cardName } from "@/lib/moves";
import { HAND_TAB_EVENT, isPhone, useBottomSpace, useDock } from "@/lib/useDock";
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
  /** The buttons over the offered card that is selected (keep it, cancel). */
  offeredActions?: CardAction[];
  onOffer?: (card: string) => void;
  /** An Exertian card is to be played (face down): the cards that can be, the one that is picked, and the buttons over it. */
  exertian?: { selectable: string[]; selected: string | null; onSelect: (card: string) => void; actions: CardAction[] };
}

/** The tab with the player's Exertian cards (ALIEN-EXE-01 to ALIEN-EXE-07): those still held, those played face down, and the milestones. */
export function ExertianTab({ view, selection }: { view: View; selection?: HandSelection }) {
  const me = view.viewer;
  const player = me === null ? undefined : view.state.players[me];
  const slot = view.state.species.find((sp) => sp.discovered && sp.species === "exertians");
  if (!player || !slot) return null;
  const tracker = view.trackers?.[player.index];
  const milestones = (slot.extra.milestones ?? []) as { at: number; cost: number; done: number[] }[];
  const danger = (tracker?.danger_cards ?? 0) + (tracker?.danger_board ?? 0);
  return (
    <div className="exertiantab">
      <section className="exgroup" aria-label="Exertian cards that can still be played">
        <h4>Available ({player.exertian_hand.length})</h4>
        <div className="excards">
          {player.exertian_hand.length === 0 ? <span className="muted">No Exertian cards left to play.</span> : null}
          {player.exertian_hand.map((c, i) => {
            const pick = selection?.exertian;
            if (!pick?.selectable.includes(c)) {
              // biome-ignore lint/suspicious/noArrayIndexKey: ids are unique, the index only guards a hidden card
              return <CardImage key={`${c}-${i}`} id={c} size="hand" />;
            }
            const on = pick.selected === c;
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: ids are unique, the index only guards a hidden card
              <span key={`${c}-${i}`} className="cardwrap">
                <button
                  type="button"
                  className={on ? "cardbtn selectable selected" : "cardbtn selectable"}
                  aria-pressed={on}
                  onClick={() => pick.onSelect(c)}
                >
                  <CardImage id={c} size="hand" />
                </button>
                {on ? <CardActions actions={pick.actions} /> : null}
              </span>
            );
          })}
        </div>
      </section>
      <section className="exgroup" aria-label="Exertian cards played face down">
        <h4>Played face down ({player.exertian_played.length})</h4>
        <div className="excards">
          {player.exertian_played.length === 0 ? <span className="muted">None played yet.</span> : null}
          {player.exertian_played.map((c, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: ids are unique, the index only guards a hidden card
            <CardImage key={`${c}-${i}`} id={c} size="hand" />
          ))}
        </div>
      </section>
      <dl className="exfacts">
        <div>
          <dt>Danger</dt>
          <dd>
            <b>{danger}</b> ({tracker?.danger_cards ?? 0} from played cards + {tracker?.danger_board ?? 0} from the species board)
          </dd>
        </div>
        <div>
          <dt>Milestones</dt>
          <dd>
            {milestones.map((m, i) => (
              <span key={m.at} className={m.done.includes(player.index) ? "exmilestone crossed" : "exmilestone"}>
                {i + 1}: {m.at} points, {m.cost > 0 ? `${m.cost} credit` : "free"}
                {m.done.includes(player.index) ? " (crossed)" : ""}
              </span>
            ))}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function HandDock({ view, selection }: { view: View; selection?: HandSelection }) {
  const [folded, toggle, set] = useDock("hand");
  const wanted = (selection?.offered?.length ?? 0) > 0 || selection?.autoOpen === true;
  const wasWanted = useRefHook(false);
  // the hand opens by itself when cards are offered, so that the player sees them
  const firstLook = useRefHook(true);
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when cards become offered
  useEffect(() => {
    // on a phone the page starts with the hand folded, whatever the game waits for: it opens by itself only when the wish comes later
    if (wanted && !wasWanted.current && !(firstLook.current && isPhone())) set(true);
    wasWanted.current = wanted;
    firstLook.current = false;
  }, [wanted]);
  const dock = useRef<HTMLElement>(null);
  useBottomSpace(dock, "hand");
  const me = view.viewer;
  const player = me === null ? undefined : view.state.players[me];
  const [tab, setTab] = useState<"hand" | "exertian" | "mascamite" | "security">("hand");
  // the keys q (the hand) and w (the other cards): they open the tab, go on to the next of the other tabs, and fold the panel after the last
  type Tab = "hand" | "exertian" | "mascamite" | "security";
  const keys = useRefHook<{ folded: boolean; tab: Tab; others: Tab[]; set: (open: boolean) => void; setTab: (t: Tab) => void } | null>(
    null,
  );
  useEffect(() => {
    const onKey = (e: Event) => {
      const k = keys.current;
      if (!k) return;
      if ((e as CustomEvent<string>).detail === "hand") {
        if (k.folded) {
          k.setTab("hand");
          k.set(true);
        } else if (k.tab === "hand") k.set(false);
        else k.setTab("hand");
        return;
      }
      if (k.others.length === 0) return;
      if (k.folded) {
        k.setTab(k.others[0] as Tab);
        k.set(true);
        return;
      }
      const next = k.others[(k.tab === "hand" ? -1 : k.others.indexOf(k.tab)) + 1];
      if (next) k.setTab(next);
      else k.set(false);
    };
    window.addEventListener(HAND_TAB_EVENT, onKey);
    return () => window.removeEventListener(HAND_TAB_EVENT, onKey);
  }, []);
  // an Exertian card is to be played: the hand opens on the Exertian tab
  const wantsExertian = (selection?.exertian?.selectable.length ?? 0) > 0;
  const wasWantedExertian = useRefHook(false);
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when a card becomes playable
  useEffect(() => {
    if (wantsExertian && !wasWantedExertian.current && !isPhone()) {
      setTab("exertian");
      set(true);
    }
    wasWantedExertian.current = wantsExertian;
  }, [wantsExertian]);
  // decided after the first render (the server does not know the width of the window)
  const [inRow, setInRow] = useState(false);
  useEffect(() => setInRow(!isPhone()), []);
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
  // the other tabs lie in the row of the header, beside the Hand button that folds the hand; on a phone that button is in the bottom bar, so the tabs stay in the body
  const extraTabs = exertians || mascamites || arkhos;

  const onHandTab = !showExertian && !showMascamite && !showSecurity;
  keys.current = {
    folded,
    tab: showExertian ? "exertian" : showMascamite ? "mascamite" : showSecurity ? "security" : "hand",
    others: [exertians ? "exertian" : null, mascamites ? "mascamite" : null, arkhos ? "security" : null].filter(
      (t): t is Tab => t !== null,
    ),
    set,
    setTab,
  };
  const tabsStrip = (
    <div className="handtabs" role="tablist">
      <button type="button" role="tab" aria-selected={onHandTab} onClick={() => setTab("hand")}>
        {inRow ? `Hand (${player.hand.length + (selection?.offered?.length ?? 0)})` : "Hand"}
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
  );
  return (
    <aside ref={dock} className={folded ? "hand dock folded" : "hand dock"} aria-label="Your hand">
      {/* on a wide screen the tabs are the header and the button that folds the hand is in its top right corner; folded, it is the tab with the count */}
      <button
        type="button"
        className={!folded && inRow ? "handtab corner" : "handtab"}
        onClick={toggle}
        aria-expanded={!folded}
        aria-label={!folded && inRow ? "Fold the hand" : undefined}
      >
        {!folded && inRow ? null : <span>Hand ({player.hand.length + (selection?.offered?.length ?? 0)})</span>}
        <span aria-hidden="true">{folded ? "▴" : "▾"}</span>
      </button>
      {!folded && inRow ? tabsStrip : null}
      {folded ? null : (
        <div className="handbody">
          {extraTabs && !inRow ? tabsStrip : null}
          {showExertian ? <ExertianTab view={view} selection={selection} /> : null}
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
                      <span key={c} className="cardwrap">
                        <button
                          type="button"
                          className={selection.offeredSelected === c ? "cardbtn selectable selected" : "cardbtn selectable"}
                          aria-pressed={selection.offeredSelected === c}
                          onClick={() => selection.onOffer?.(c)}
                        >
                          <CardImage id={c} size="hand" />
                        </button>
                        {selection.offeredSelected === c && selection.offeredActions ? (
                          <CardActions actions={selection.offeredActions} />
                        ) : null}
                      </span>
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
export function ExertianDock({ view, selection }: { view: View; selection?: HandSelection }) {
  const [folded, toggle, set] = useDock("exertian");
  // the dock opens by itself when an Exertian card is to be played (on a phone it starts folded; not at the first look at the page)
  const wantsCard = (selection?.exertian?.selectable.length ?? 0) > 0;
  const wasWanted = useRefHook(false);
  const firstLook = useRefHook(true);
  // biome-ignore lint/correctness/useExhaustiveDependencies: only when a card becomes playable
  useEffect(() => {
    if (wantsCard && !wasWanted.current && !(firstLook.current && isPhone())) set(true);
    wasWanted.current = wantsCard;
    firstLook.current = false;
  }, [wantsCard]);
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
          <ExertianTab view={view} selection={selection} />
        </div>
      )}
    </aside>
  );
}
