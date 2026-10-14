// The alien species of the game. The boards themselves are drawn at the top of the main board (BoardView); the discovery spaces can be read there.
// What is added here is the part the picture does not show: which species a face-up board is, and the markers on it by trace colour.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";

const TRACE_COLOR: Record<string, string> = { pink: "#e0457b", yellow: "#e0a800", blue: "#2f8fd8" };
const label = (name: string): string => name.charAt(0).toUpperCase() + name.slice(1);

export function AlienNotes({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const color = (i: number): string => PLAYER_COLOR[s.players[i]?.color ?? "white"] ?? "#ffffff";
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  const shown = s.species.map((sp, i) => ({ sp, i })).filter(({ sp }) => sp.discovered || sp.complete);
  if (shown.length === 0) return null;
  return (
    <section className="aliennotes" aria-label="Alien species">
      {shown.map(({ sp, i }) => (
        <div key={i} className="alien">
          <b>Species {i + 1}: </b>
          {sp.discovered ? label(sp.species) : <span className="muted">turns face up when the turn ends</span>}
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
        </div>
      ))}
    </section>
  );
}
