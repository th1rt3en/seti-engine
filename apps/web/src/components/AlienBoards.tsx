// The two alien species of the game. An undiscovered species shows the back of its board; once discovered the board is turned face up.
// Under each board: its three discovery spaces and the markers on the board by trace colour.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";

const SPECIES = assets.species as Record<string, string>;
const TRACE_COLOR: Record<string, string> = { pink: "#e0457b", yellow: "#e0a800", blue: "#2f8fd8" };
const TRACE_ORDER = ["pink", "yellow", "blue"];
const label = (name: string): string => name.charAt(0).toUpperCase() + name.slice(1);

export function AlienBoards({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const color = (i: number): string => PLAYER_COLOR[s.players[i]?.color ?? "white"] ?? "#ffffff";
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  return (
    <section className="aliens" aria-label="Alien species">
      {s.species.map((sp, i) => {
        const face = sp.discovered ? (SPECIES[sp.species] ?? SPECIES.back) : SPECIES.back;
        const title = sp.discovered ? label(sp.species) : "Undiscovered species";
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: the two slots are fixed
          <figure key={i} className="alien">
            <img
              src={face}
              alt={`${title} (species ${i + 1})`}
              width={300}
              height={546}
              loading="lazy"
              decoding="async"
              className={sp.discovered ? "alienimg" : "alienimg hidden"}
            />
            <figcaption>
              <b>Species {i + 1}: </b>
              {title}
              {!sp.discovered && sp.complete ? <span className="muted"> (turns face up when the turn ends)</span> : null}
              <div className="row small">
                <span className="muted">Discovery spaces</span>
                {TRACE_ORDER.map((c, k) => {
                  const mark = sp.discovery_spaces[k];
                  const neutral = mark === "n";
                  return (
                    <span
                      key={c}
                      className="dot"
                      style={{
                        borderColor: TRACE_COLOR[c],
                        background: mark == null ? "transparent" : neutral ? "#8b94a3" : color(Number(mark.slice(1))),
                      }}
                      title={mark == null ? `${c}: free` : neutral ? `${c}: neutral marker` : `${c}: ${who(Number(mark.slice(1)))}`}
                    />
                  );
                })}
              </div>
              {sp.discovered ? (
                <div className="small">
                  {Object.entries(sp.board).map(([c, spaces]) => {
                    const markers = spaces.flat();
                    return (
                      <div key={c} className="row">
                        <span style={{ color: TRACE_COLOR[c] ?? "inherit" }}>{c}</span>
                        {markers.length === 0 ? <span className="muted">no markers</span> : null}
                        {markers.map((player, k) => (
                          <span
                            // biome-ignore lint/suspicious/noArrayIndexKey: placement order
                            key={k}
                            className="dot small"
                            style={{ background: color(player) }}
                            title={who(player)}
                          />
                        ))}
                      </div>
                    );
                  })}
                  {sp.overflow.length > 0 ? <div className="muted">Overflow markers: {sp.overflow.map(who).join(", ")}</div> : null}
                </div>
              ) : null}
            </figcaption>
          </figure>
        );
      })}
    </section>
  );
}
