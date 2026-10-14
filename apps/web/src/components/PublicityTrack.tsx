// The publicity track, cut out of the base board and turned the right way up (the lower part of the board is printed upside down), with a
// marker for every player at their publicity.
import { PUBLICITY_CELL } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import { PieceDefs, PublicityPawn, pieceColor } from "./Pieces";

export function PublicityTrack({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  const art = assets.publicity;
  return (
    <figure className="publicity">
      <svg viewBox={`0 0 ${art.w} ${art.h}`} role="img" aria-label="Publicity track">
        <PieceDefs />
        <image href={art.src} x={0} y={0} width={art.w} height={art.h} />
        {s.players.map((p) => {
          const level = Math.min(10, Math.max(0, p.publicity));
          return (
            <PublicityPawn
              key={p.index}
              x={PUBLICITY_CELL.x0 + p.index * PUBLICITY_CELL.dx}
              y={PUBLICITY_CELL.y0 - level * PUBLICITY_CELL.dy}
              size={104}
              color={pieceColor(p.color)}
              title={`${who(p.index)}: ${p.publicity} publicity`}
            />
          );
        })}
      </svg>
      <figcaption className="small muted">Publicity</figcaption>
    </figure>
  );
}
