"use client";
// The reward spaces of an organization board (Cosmos Strategy Group, Helion Assembly) that can be marked, shown in the context bar: the strip of the
// board that holds the spaces, cropped from the picture of the card. A space that can be marked now is clickable, one that was marked before is
// covered by the player's own marker (EXP-ORG-11).
import { cardImage } from "@/lib/cardImages";
import { ORG_SPACES } from "@/lib/targets";
import { Marker, type PieceColor, PieceDefs } from "./Pieces";

const WIDTH = 560;
const HEIGHT = 421;
const RADIUS = 34;

export function OrgMarkPick({
  org,
  options,
  marked,
  color,
  picked,
  onPick,
}: {
  org: string;
  /** The spaces that can be marked now. */
  options: string[];
  /** The spaces that were marked before. */
  marked: string[];
  color: PieceColor;
  picked: string | null;
  onPick: (space: string) => void;
}) {
  const spaces = ORG_SPACES[org];
  if (!spaces) return null;
  const at = Object.values(spaces);
  const xs = at.map((p) => p[0]);
  const ys = at.map((p) => p[1]);
  const pad = RADIUS + 28;
  const left = Math.max(0, Math.min(...xs) - pad);
  const top = Math.max(0, Math.min(...ys) - pad);
  const w = Math.min(WIDTH, Math.max(...xs) + pad) - left;
  const h = Math.min(HEIGHT, Math.max(...ys) + pad) - top;
  return (
    <svg viewBox={`${left} ${top} ${w} ${h}`} className="orgmarkpick" style={{ maxWidth: 330, width: "100%", display: "block" }}>
      <title>{`Reward spaces of ${org.replaceAll("_", " ")}`}</title>
      <PieceDefs />
      <image href={cardImage(org)} x={0} y={0} width={WIDTH} height={HEIGHT} />
      {Object.entries(spaces).map(([space, [x, y]]) => {
        if (marked.includes(space))
          return <Marker key={space} x={x} y={y} size={RADIUS * 2.2} color={color} title={`${space}: already marked`} />;
        if (!options.includes(space)) return null;
        const on = picked === space;
        return (
          <g
            key={space}
            // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
            role="button"
            tabIndex={0}
            aria-label={`Mark the ${space.replaceAll("_", " ")} space`}
            aria-pressed={on}
            className={on ? "spot chosen" : "spot"}
            onClick={() => onPick(space)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onPick(space)}
          >
            <circle cx={x} cy={y} r={RADIUS} className="spotshape panelspot" />
          </g>
        );
      })}
    </svg>
  );
}
