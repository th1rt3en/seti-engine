// The translation board of the Glyphids (EXP-GLY-02, EXP-GLY-05): the picture that matches the sides of the two strips, the glyph tokens that
// have been placed on it, and the glyph tokens each player holds (they score by sets at the end, EXP-GLY-07).
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import expansionAssets from "../generated/expansion-assets.json";

const ASSET = expansionAssets as Record<string, string>;
// the four arrangements: [top strip side, bottom strip side] -> the picture (a to d, A-044)
const VARIANT: Record<string, string> = { "0,0": "a", "1,1": "b", "1,0": "c", "0,1": "d" };
// centres of the holes in the 750 x 690 picture
const TOP = [
  [200, 160],
  [375, 160],
  [545, 160],
];
const BOTTOM = [
  [112, 440],
  [290, 440],
  [468, 440],
  [640, 440],
];
const token = (glyph: string): string | undefined => ASSET[`tokens/glyphids-token-${glyph === "blue" ? "bue" : glyph}`];

export function GlyphidsPanel({ view, names }: { view: View; names: string[] }) {
  const s = view.state;
  const slot = s.species.find((sp) => sp.discovered && sp.species === "glyphids");
  if (!slot) return null;
  const extra = slot.extra as {
    sides?: number[];
    top?: (string | null)[];
    bottom?: (string | null)[];
    tokens?: Record<string, string>;
    supply?: string[];
  };
  const variant = VARIANT[(extra.sides ?? [0, 0]).join(",")] ?? "a";
  const src = ASSET[`boards/glyphids-track-${variant}`];
  if (!src) return null;
  const size = 105;
  const place = (rows: (string | null)[] | undefined, spots: number[][], key: string) =>
    (rows ?? []).map((g, i) => {
      const at = spots[i];
      const href = g ? token(g) : undefined;
      const [x, y] = at ?? [];
      if (x === undefined || y === undefined || !href) return null;
      return <image key={`${key}-${i}`} href={href} x={x - size / 2.1} y={y - size / 1.9} width={size * 0.95} height={size * 1.1} />;
    });
  return (
    <section className="card glyphpanel" aria-label="Glyphids translation board">
      <h3>Glyphids translation board</h3>
      <svg
        viewBox="0 0 750 690"
        className="translation"
        role="img"
        aria-label="The translation board with the glyph tokens that have been placed"
      >
        <rect x="0" y="0" width="750" height="690" fill="#0b1b0e" />
        <image href={src} x="0" y="0" width="750" height="690" />
        {place(extra.top, TOP, "t")}
        {place(extra.bottom, BOTTOM, "b")}
      </svg>
      <p className="small muted">
        {Object.keys(extra.tokens ?? {}).length} glyph tokens still lie on the board, planets, sectors and techs;{" "}
        {extra.supply?.length ?? 0} in the supply.
      </p>
      <ul className="plain glyphhold">
        {s.players.map((p) => (
          <li key={p.index}>
            <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} /> {names[p.index] ?? `Player ${p.index + 1}`}{" "}
            {p.glyphs.length === 0 ? <span className="muted small">no glyph tokens</span> : null}
            {p.glyphs.map((g, i) => (
              <img
                // biome-ignore lint/suspicious/noArrayIndexKey: tokens of a kind are alike
                key={`${g}-${i}`}
                src={token(g)}
                alt={`${g} glyph`}
                title={`${g} glyph token`}
                width={22}
                height={26}
              />
            ))}
          </li>
        ))}
      </ul>
    </section>
  );
}
