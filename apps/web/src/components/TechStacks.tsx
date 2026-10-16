// The twelve tech stacks, each cut out of the base board and turned the right way up, one above the other. On every stack lies its top tile
// (the bonus on it is what the next player to take it gets), the +2 tile while the first taker has not come, and a count of the tiles left.
import { glyphToken } from "@/lib/glyphids";
import { TECH_INFO } from "@/lib/techs";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";

const CATEGORIES = [
  { key: "probe", label: "Probe techs" },
  { key: "telescope", label: "Telescope techs" },
  { key: "computer", label: "Computer techs" },
] as const;
const GLYPHS = ["dot", "link", "branch", "cross"] as const;

interface Crop {
  src: string;
  w: number;
  h: number;
  pocket: { x: number; y: number; w: number; h: number };
}
const STACKS = assets.stacks as Record<string, Crop>;
const TILES = assets.tiles as Record<string, string>;
const BONUS_NAME: Record<string, string> = { vp3: "3 points", card: "1 card", energy: "1 energy", publicity: "1 publicity" };

/** Picking a tech: the stacks (by their place in the state) that can be taken now, the one that is picked, and what a click does. */
export interface TechPick {
  selectable: number[];
  selected: number | null;
  onSelect: (stack: number) => void;
  /** The button that makes the move, lying on the selected tech (the context bar above asks the question). */
  onConfirm?: () => void;
}

export function TechStacks({ view, pick }: { view: View; pick?: TechPick }) {
  const stacks = view.state.tech_stacks;
  // the glyph tokens that lie on tech stacks with their +2 tile (EXP-GLY-03)
  const glyphs = (view.state.species.find((sp) => sp.discovered && sp.species === "glyphids")?.extra.tokens ?? {}) as Record<
    string,
    string
  >;
  return (
    <section className="techstacks" aria-label="Tech stacks">
      {CATEGORIES.map((cat) => (
        <div key={cat.key}>
          <h3>{cat.label}</h3>
          <div className="techrow">
            {GLYPHS.map((glyph) => {
              const crop = STACKS[`${cat.key}-${glyph}`];
              const stack = stacks.find((x) => x.category === cat.key && x.glyph === glyph);
              if (!crop) return null;
              const top = stack?.tiles[0];
              const tileSrc = top ? TILES[`${cat.key}-${glyph}-${top}`] : undefined;
              const { pocket } = crop;
              const left = stack?.tiles.length ?? 0;
              const index = stacks.findIndex((x) => x.category === cat.key && x.glyph === glyph);
              const info = TECH_INFO[`${cat.key}-${glyph}`];
              const label = `${info?.name ?? `${cat.key} tech ${glyph}`} (${info?.effect ?? ""}): ${left} tiles left${top ? `, top tile gives ${BONUS_NAME[top] ?? top}` : ""}${stack?.two_point_tile ? ", the +2 tile is still on top" : ""}`;
              const art = (
                <svg viewBox={`0 0 ${crop.w} ${crop.h}`} className="stack" role="img" aria-label={label}>
                  <image href={crop.src} x={0} y={0} width={crop.w} height={crop.h} />
                  {tileSrc ? (
                    <image
                      href={tileSrc}
                      x={pocket.x}
                      y={pocket.y}
                      width={pocket.w}
                      height={pocket.h}
                      preserveAspectRatio="xMidYMid slice"
                    />
                  ) : null}
                  {stack?.two_point_tile ? (
                    <image
                      href={assets.twoPoint}
                      x={pocket.x + pocket.w * 0.04}
                      y={pocket.y + 6}
                      width={pocket.w * 0.92}
                      height={pocket.w * 0.92 * (120 / 179)}
                    />
                  ) : null}
                  {stack?.two_point_tile && glyphs[`tech:${index}`] ? (
                    <image
                      href={glyphToken(glyphs[`tech:${index}`] ?? "")}
                      x={pocket.x - 6}
                      y={pocket.y + pocket.h - 74}
                      width={58}
                      height={66}
                    >
                      <title>{`${glyphs[`tech:${index}`]} glyph token: taken with this tech`}</title>
                    </image>
                  ) : null}
                  <g transform={`translate(${pocket.x + pocket.w - 30} ${pocket.y + pocket.h - 30})`}>
                    <circle r={26} fill="rgba(8,12,26,0.88)" stroke="#fff" strokeWidth={4} />
                    <text y={12} fontSize={34} fontWeight={700} fill="#fff" textAnchor="middle">
                      {left}
                    </text>
                  </g>
                  <title>{label}</title>
                </svg>
              );
              if (!pick?.selectable.includes(index)) return <span key={`${cat.key}-${glyph}`}>{art}</span>;
              return (
                <span key={`${cat.key}-${glyph}`} className="stackwrap">
                  <button
                    type="button"
                    className={pick.selected === index ? "stackbtn selected" : "stackbtn"}
                    aria-pressed={pick.selected === index}
                    title={`Take ${info?.name ?? "this tech"}`}
                    onClick={() => pick.onSelect(index)}
                  >
                    {art}
                  </button>
                  {pick.selected === index && pick.onConfirm ? (
                    <button type="button" className="primary stackconfirm" onClick={pick.onConfirm}>
                      Confirm
                    </button>
                  ) : null}
                </span>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}
