"use client";
import { cardImage } from "@/lib/cardImages";
// The organization module (EXP-ORG-*, EXP-QS-*): every player's organization and quick start cards, the neutral quick start cards, the tiles of
// Xenolab, the reward spaces marked on Cosmos Strategy Group and Helion Assembly, and the card prepared by Futurespan. What the organization can
// do now (its abilities, the reward space to mark) is offered as highlighted places on its card.
import { ORG_SPACES } from "@/lib/targets";
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { CardImage } from "./CardImage";
import { OrgName } from "./OrgName";
import { PlayerName } from "./PlayerName";

const ASSET = expansionAssets as Record<string, string>;
const TILES = ["launch", "scan", "research"] as const; // tile 1, 2, 3 of Xenolab

export function OrgPanel({ view, names, spots }: { view: View; names: string[]; spots?: BoardSpots }) {
  const s = view.state;
  const mine = (spots?.items ?? []).filter((sp) => sp.panel === "org");
  // folded until the player opens it; it opens by itself when something is to be done on it (a reward space to mark, an ability to use)
  const [open, setOpen] = useState(false);
  const needed = mine.length > 0;
  useEffect(() => {
    if (needed) setOpen(true);
  }, [needed]);
  if (!s.options.expansion) return null;
  const players = s.players.filter((p) => p.organization && !(s.rival && p.index === s.rival.index));
  if (players.length === 0 && s.neutral_quick.length === 0) return null;
  return (
    <details
      className="card exppanel orgpanel"
      aria-label="Organizations and quick start cards"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>
        <h3>Organizations and quick start cards</h3>
      </summary>
      {players.map((p) => {
        const tiles = p.org_data?.tiles as Record<string, boolean> | undefined;
        const fsCard = p.org_data?.fs_card as string | undefined;
        const fsToken = p.org_data?.fs_token as number | undefined;
        const spaces = ORG_SPACES[p.organization ?? ""];
        const canAct = p.index === view.viewer && mine.length > 0;
        return (
          <div key={p.index} style={{ marginBottom: 10 }}>
            <b className="small">
              <PlayerName seat={p.index} name={names[p.index] ?? `Player ${p.index + 1}`} />
            </b>{" "}
            <OrgName id={p.organization ?? ""} className="orgname" />
            {spaces ? (
              // the reward spaces are on the organization board itself: a marked one is crossed, a space that can be marked is highlighted
              <svg
                viewBox="0 0 560 421"
                className="panelsvg orgboard"
                role="img"
                aria-label={`${p.organization} board with its reward spaces`}
              >
                <image href={cardImage(p.organization ?? "")} x={0} y={0} width={560} height={421} />
                {Object.entries(spaces).map(([name, at]) =>
                  p.org_marks.includes(name) ? (
                    <g key={name}>
                      <circle cx={at[0]} cy={at[1]} r={32} fill="rgba(0,0,0,0.55)" />
                      <path
                        d={`M ${at[0] - 18} ${at[1] - 18} L ${at[0] + 18} ${at[1] + 18} M ${at[0] + 18} ${at[1] - 18} L ${at[0] - 18} ${at[1] + 18}`}
                        stroke="#fff"
                        strokeWidth={7}
                      />
                      <title>{`${name}: marked`}</title>
                    </g>
                  ) : null,
                )}
              </svg>
            ) : (
              <div className={canAct ? "orgcard selectable" : "orgcard"}>
                <CardImage id={p.organization ?? ""} width={220} />
              </div>
            )}
            {tiles ? (
              <div className="tiles" aria-label="Xenolab tiles">
                {TILES.map((t, i) => (
                  <img
                    key={t}
                    src={ASSET[`tokens/xenolab-tile-${i + 1}${tiles[t] ? "" : "-back"}`]}
                    alt={`${t} tile, ${tiles[t] ? "ready" : "used"}`}
                    title={`${t} tile: ${tiles[t] ? "ready" : "used (flips back with a life trace of its color)"}`}
                  />
                ))}
              </div>
            ) : null}
            {p.org_marks.length > 0 && !spaces ? <p className="small muted">Marked reward spaces: {p.org_marks.join(", ")}</p> : null}
            {fsToken !== undefined ? (
              <p className="small muted">
                Futurespan token at {fsToken} points{fsCard ? "; a card is prepared (face down)" : "; no card is prepared"}.
                {fsCard && fsCard !== "?" ? <CardImage id={fsCard} width={90} /> : null}
              </p>
            ) : null}
            {p.org_used ? <p className="small muted">The once-per-round ability has been used.</p> : null}
            {p.quick_start.length > 0 ? (
              // the quick start cards are hidden until the player wants to look at them
              <details className="qfold">
                <summary className="small muted">Quick start cards ({p.quick_start.length})</summary>
                <div className="qcards">
                  {p.quick_start.map((c) => (
                    <CardImage key={c} id={c} width={100} />
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        );
      })}
      {s.neutral_quick.length > 0 ? (
        <>
          <details className="qfold">
            <summary className="small muted">Neutral quick start cards (marked with white pieces) ({s.neutral_quick.length})</summary>
            <div className="qcards">
              {s.neutral_quick.map((c) => (
                <CardImage key={c} id={c} width={100} />
              ))}
            </div>
          </details>
        </>
      ) : null}
    </details>
  );
}
