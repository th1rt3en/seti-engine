import { GLYPH_HOLES, TRACK_PICTURE } from "@/lib/glyphids";
// The translation board of the Glyphids (EXP-GLY-02, EXP-GLY-05) drawn in the 750 x 690 coordinates of its picture: the cleaned frame with its
// two combs, the scoring reminder (EXP-GLY-07) and the rewards of the strips for the arrangement that was drawn (A-044). Used by the game board
// and by the side panel; glyph tokens are placed over it by the caller.
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";

const ASSET = expansionAssets as Record<string, string>;
const PRINTED = assets.printedIcons as Record<string, string>;
const ICON: Record<string, string | undefined> = {
  credit: ASSET["tokens/icon-credit"],
  energy: ASSET["tokens/icon-energy"],
  data: ASSET["tokens/icon-data"],
  publicity: ASSET["tokens/icon-publicity"],
  vp: ASSET["tokens/icon-score"],
  signal_token: ASSET["tokens/token-signal"],
  card_random: PRINTED["card-random"],
};
const NAME: Record<string, string> = {
  credit: "credit",
  energy: "energy",
  data: "data",
  publicity: "publicity",
  vp: "points",
  signal_token: "signal token",
  card_random: "random card",
};
// what each strip gives, by side (docs/spec/data/expansion-glyphids.json); a victory-points reward is worth 3
const TOP_SIDE = [
  ["credit", "energy", "signal_token"],
  ["energy", "signal_token", "credit"],
];
const BOTTOM_SIDE = [
  ["data", "card_random", "vp", "publicity"],
  ["card_random", "publicity", "data", "vp"],
];
const STRIP_Y = { top: 300, bottom: 567 };
// the scoring reminder: centres along the bar, from the layout of the printed board
const BAR = { y: 50, back: 121, notEqual: 159 };
const SETS: { points: number; number: number; icon: number; slash?: number }[] = [
  { points: 1, number: 188, icon: 213, slash: 235 },
  { points: 3, number: 251, icon: 275, slash: 297 },
  { points: 5, number: 313, icon: 338, slash: 359 },
  { points: 8, number: 376, icon: 400, slash: 422 },
  { points: 11, number: 446, icon: 479, slash: 500 },
  { points: 15, number: 524, icon: 557, slash: 579 },
  { points: 20, number: 603, icon: 635 },
];

/** Where the pieces of the translation board are, in picture pixels (for tests and for the callers). */
export const TRANSLATION = { ...TRACK_PICTURE, holes: GLYPH_HOLES };

export function TranslationBoard({ sides }: { sides?: number[] }) {
  const frame = ASSET["boards/glyphids-frame"];
  const top = TOP_SIDE[sides?.[0] ?? 0] ?? [];
  const bottom = BOTTOM_SIDE[sides?.[1] ?? 0] ?? [];
  const reward = (kind: string, cx: number, cy: number, key: string) => {
    const href = ICON[kind];
    const h = 64;
    const w = kind === "card_random" ? 46 : 64;
    return (
      <g key={key}>
        <title>{`1 ${NAME[kind] ?? kind}`.replace("1 points", "3 points")}</title>
        <text x={cx - 32} y={cy + 2} className="glyphnum" fontSize="42" textAnchor="middle" dominantBaseline="central">
          {kind === "vp" ? 3 : 1}
        </text>
        {href ? <image href={href} x={cx + 18 - w / 2} y={cy - h / 2} width={w} height={h} /> : null}
      </g>
    );
  };
  return (
    <g>
      {frame ? <image href={frame} x="0" y="0" width={TRACK_PICTURE.w} height={TRACK_PICTURE.h} /> : null}
      <g>
        <title>At the end of the game: points for the number of different glyph tokens a player owns (1, 2, 3, 4, 5, 6, 7 kinds)</title>
        <rect x="90" y="18" width="570" height="64" rx="20" fill="#7a5a14" />
        <rect x="93" y="21" width="564" height="58" rx="17" fill="#d9b04a" />
        <image href={ASSET["tokens/glyphids-token-back"]} x={BAR.back - 20} y={BAR.y - 20} width="40" height="40" />
        <text x={BAR.notEqual} y={BAR.y} className="glyphbar" fontSize="23" textAnchor="middle" dominantBaseline="central">
          ≠
        </text>
        {SETS.map((s) => (
          <g key={s.points}>
            <text x={s.number} y={BAR.y + 1} className="glyphbar" fontSize="23" textAnchor="middle" dominantBaseline="central">
              {s.points}
            </text>
            <image href={ICON.vp} x={s.icon - 13.5} y={BAR.y - 13.5} width="27" height="27" />
            {s.slash ? (
              <text x={s.slash} y={BAR.y} className="glyphbar slash" fontSize="23" textAnchor="middle" dominantBaseline="central">
                /
              </text>
            ) : null}
          </g>
        ))}
      </g>
      {top.map((kind, i) => reward(kind, GLYPH_HOLES.top[i]?.[0] ?? 0, STRIP_Y.top, `t${i}`))}
      {bottom.map((kind, i) => reward(kind, GLYPH_HOLES.bottom[i]?.[0] ?? 0, STRIP_Y.bottom, `b${i}`))}
    </g>
  );
}
