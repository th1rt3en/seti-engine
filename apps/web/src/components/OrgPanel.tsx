// The organization module (EXP-ORG-*, EXP-QS-*): every player's organization and quick start cards, the neutral quick start cards, the tiles of
// Xenolab, the reward spaces marked on Cosmos Strategy Group and Helion Assembly, and the card prepared by Futurespan. What the organization can
// do now (its abilities, the reward space to mark) is offered as highlighted places on its card.
import { type Move, describeMove } from "@/lib/moves";
import type { View } from "@seti/protocol";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { CardImage } from "./CardImage";

const ASSET = expansionAssets as Record<string, string>;
const TILES = ["launch", "scan", "research"] as const; // tile 1, 2, 3 of Xenolab

export function OrgPanel({ view, names, spots }: { view: View; names: string[]; spots?: BoardSpots }) {
  const s = view.state;
  if (!s.options.expansion) return null;
  const legal = view.legal as Move[];
  const mine = (spots?.items ?? []).filter((sp) => sp.panel === "org");
  const players = s.players.filter((p) => p.organization && !(s.rival && p.index === s.rival.index));
  if (players.length === 0 && s.neutral_quick.length === 0) return null;
  return (
    <section className="card exppanel" aria-label="Organizations and quick start cards">
      <h3>Organizations</h3>
      {players.map((p) => {
        const tiles = p.org_data?.tiles as Record<string, boolean> | undefined;
        const fsCard = p.org_data?.fs_card as string | undefined;
        const fsToken = p.org_data?.fs_token as number | undefined;
        const canAct = p.index === view.viewer && mine.length > 0;
        return (
          <div key={p.index} style={{ marginBottom: 10 }}>
            <b className="small">{names[p.index] ?? `Player ${p.index + 1}`}</b>
            <div className={canAct ? "orgcard selectable" : "orgcard"}>
              <CardImage id={p.organization ?? ""} width={220} />
            </div>
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
            {p.org_marks.length > 0 ? <p className="small muted">Marked reward spaces: {p.org_marks.join(", ")}</p> : null}
            {fsToken !== undefined ? (
              <p className="small muted">
                Futurespan token at {fsToken} points{fsCard ? "; a card is prepared (face down)" : "; no card is prepared"}.
                {fsCard && fsCard !== "?" ? <CardImage id={fsCard} width={90} /> : null}
              </p>
            ) : null}
            {p.org_used ? <p className="small muted">The once-per-round ability has been used.</p> : null}
            {p.quick_start.length > 0 ? (
              <div className="qcards">
                {p.quick_start.map((c) => (
                  <CardImage key={c} id={c} width={100} />
                ))}
              </div>
            ) : null}
            {canAct ? (
              <div className="chips">
                {mine.map((sp) => (
                  <button
                    key={sp.id}
                    type="button"
                    className={spots?.selected === sp.id ? "chip chosen" : "chip"}
                    aria-pressed={spots?.selected === sp.id}
                    onClick={() => spots?.onSelect(sp.id)}
                  >
                    {describeMove(legal[sp.move] as Move)}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
      {s.neutral_quick.length > 0 ? (
        <>
          <b className="small">Neutral quick start cards (marked with white pieces)</b>
          <div className="qcards">
            {s.neutral_quick.map((c) => (
              <CardImage key={c} id={c} width={100} />
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
