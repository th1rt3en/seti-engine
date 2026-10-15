// The translation board of the Glyphids (EXP-GLY-02, EXP-GLY-05): the picture that matches the sides of the two strips, the glyph tokens that
// have been placed on it, and the glyph tokens each player holds (they score by sets at the end, EXP-GLY-07).
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { PanelSpots } from "./PanelSpots";
import { TranslationBoard } from "./TranslationBoard";

const ASSET = expansionAssets as Record<string, string>;
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

export function GlyphidsPanel({ view, names, spots }: { view: View; names: string[]; spots?: BoardSpots }) {
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
  const size = 105;
  const place = (rows: (string | null)[] | undefined, spots: number[][], key: string) =>
    (rows ?? []).map((g, i) => {
      const at = spots[i];
      const href = g ? token(g) : undefined;
      const [x, y] = at ?? [];
      if (x === undefined || y === undefined || !href) return null;
      // biome-ignore lint/suspicious/noArrayIndexKey: the holes of a row are fixed
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
        <TranslationBoard sides={extra.sides} />
        {place(extra.top, TOP, "t")}
        {place(extra.bottom, BOTTOM, "b")}
        {/* the holes a glyph token can be placed in (EXP-GLY-05): each carries the token that would go there, a hole that takes several kinds shows them side by side */}
        <PanelSpots
          spots={spots}
          panel="glyphids"
          render={(sp) => {
            const same = (spots?.items ?? []).filter(
              (o) =>
                o.panel === "glyphids" &&
                o.shape.kind === "circle" &&
                sp.shape.kind === "circle" &&
                o.shape.x === sp.shape.x &&
                o.shape.y === sp.shape.y,
            );
            const k = same.findIndex((o) => o.id === sp.id);
            const href = sp.glyph ? token(sp.glyph) : undefined;
            if (!href || sp.shape.kind !== "circle") return null;
            const w = same.length > 1 ? 58 : 80;
            return (
              <image
                href={href}
                x={sp.shape.x - (same.length * w) / 2 + k * w}
                y={sp.shape.y - w * 0.6}
                width={w}
                height={w * 1.15}
                opacity={0.85}
              />
            );
          }}
        />
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
