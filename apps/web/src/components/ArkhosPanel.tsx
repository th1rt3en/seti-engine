"use client";
// Arkhos (EXP-ARK-01 to EXP-ARK-07): the exploration card that was revealed last, the sizes of the exploration deck, and every player's security
// cards (their own face up, the others' face down with only the trace color showing). A breach is made by clicking the security card of that color.
import { EXPLORATION_PREVIEW_EVENT, possibleExploration } from "@/lib/arkhosExploration";
import { cardImage } from "@/lib/cardImages";
import type { Spot } from "@/lib/targets";
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { CardImage } from "./CardImage";
import { PlayerName } from "./PlayerName";

const ASSET = expansionAssets as Record<string, string>;
const COLORS = ["pink", "yellow", "blue"] as const;

function ExplorationPreview({ deck, aside, revealed, onClose }: { deck: number; aside: number; revealed: string[]; onClose: () => void }) {
  const possible = possibleExploration(deck, revealed);
  const row = (ids: string[], what: string) => (
    <div className="explorationrow">
      {ids.map((id) => (
        <img key={id} src={cardImage(id)} alt={`${what}: exploration card ${id}`} title={id} loading="lazy" />
      ))}
    </div>
  );
  return (
    <div className="explorationpreview">
      <header>
        <h4>Exploration deck</h4>
        <button type="button" className="secondary" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <p className="small muted">
        {deck} cards in the deck, {aside} set aside. The order is secret, so any card that is not revealed can come next. When the deck runs
        out all 9 cards are shuffled again (5 in the deck, 4 set aside) and this list starts over.
      </p>
      <h5>Could be revealed next ({possible.length})</h5>
      {row(possible, "Possible")}
      <h5>Revealed ({revealed.length})</h5>
      {revealed.length > 0 ? row(revealed, "Revealed") : <p className="small muted">No card has been revealed since the last shuffle.</p>}
    </div>
  );
}

export function ArkhosPanel({ view, names, spots }: { view: View; names: string[]; spots?: BoardSpots }) {
  const [previewing, setPreviewing] = useState(false);
  useEffect(() => {
    const open = () => setPreviewing(true);
    window.addEventListener(EXPLORATION_PREVIEW_EVENT, open);
    return () => window.removeEventListener(EXPLORATION_PREVIEW_EVENT, open);
  }, []);
  const s = view.state;
  const slot = s.species.find((sp) => sp.discovered && sp.species === "arkhos");
  if (!slot) return null;
  const extra = slot.extra as { explore_deck?: string[]; explore_aside?: string[]; explore_discard?: string[] };
  const last = extra.explore_discard?.[extra.explore_discard.length - 1];
  const breach = (spots?.items ?? []).filter((sp: Spot) => sp.panel === "arkhos");
  return (
    <section className="card exppanel" aria-label="Arkhos">
      <h3>Arkhos</h3>
      <p className="small muted">
        Exploration deck (beside the species board): {extra.explore_deck?.length ?? 0} cards · set aside: {extra.explore_aside?.length ?? 0}{" "}
        · revealed: {extra.explore_discard?.length ?? 0}{" "}
        <button type="button" className="link" onClick={() => setPreviewing((v) => !v)} aria-expanded={previewing}>
          {previewing ? "Hide the exploration cards" : "Look at the exploration cards"}
        </button>
      </p>
      {previewing ? (
        <ExplorationPreview
          deck={extra.explore_deck?.length ?? 0}
          aside={extra.explore_aside?.length ?? 0}
          revealed={extra.explore_discard ?? []}
          onClose={() => setPreviewing(false)}
        />
      ) : null}
      {s.players.map((p) => {
        if (s.rival && p.index === s.rival.index) return null;
        if (p.index === view.viewer) return null; // your own security cards are in the Security tab of your hand
        const entries = COLORS.filter((c) => p.security?.[c] !== undefined);
        const open = Object.keys(p.security ?? {}).length === 0;
        return (
          <div key={p.index}>
            <b className="small">
              <PlayerName seat={p.index} name={names[p.index] ?? `Player ${p.index + 1}`} />
            </b>{" "}
            <span className="muted small">
              {open ? "all security cards breached: every space is open" : `${entries.length} security cards`}
            </span>
            <div className="sec">
              {entries.map((c) => {
                const id = p.security?.[c] ?? "?";
                const src = id === "?" || !cardImage(id) ? ASSET[`arkhos/security-back-${c}`] : cardImage(id);
                const spot = p.index === view.viewer ? breach.find((b) => b.glyph === c) : undefined;
                return spot && spots ? (
                  <button
                    key={c}
                    type="button"
                    className={spots.selected === spot.id ? "selectable chosen" : "selectable"}
                    aria-pressed={spots.selected === spot.id}
                    onClick={() => spots.onSelect(spot.id)}
                    style={{ width: "30%", padding: 0, border: 0, background: "none" }}
                  >
                    <img
                      src={src}
                      alt={`Breach the ${c} security card`}
                      title={`Breach the ${c} security card`}
                      style={{ width: "100%" }}
                    />
                  </button>
                ) : (
                  <img key={c} src={src} alt={`${c} security card`} title={`${c} security card`} />
                );
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}
