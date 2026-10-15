import { CENTER } from "@/lib/geometry";
import assets from "../generated/assets.json";
// An Anomaly token on the outermost ring of the solar system (ALIEN-ANO-01): a hexagon in the colour of its life trace column with the reward of the
// side that is up. The owner supplied the pictures of five of the six faces (`anomalyTokens` in assets.json); the face that is missing (yellow, 1 card)
// is still drawn as a hexagon (docs/asset-gaps.md).
import expansionAssets from "../generated/expansion-assets.json";
import { CreditIcon, DataIcon, DeckCardIcon, EnergyIcon, PublicityIcon } from "./Icons";

export type AnomalyToken = { sector: number; color: string; side: number; reward?: { t: string; n: number }[] };

const COLORS: Record<string, string> = { pink: "#e0559a", yellow: "#f2c230", blue: "#3a9bff" };
const ICONS: Record<string, (size: number) => React.ReactNode> = {
  // the points icon is a picture, which an <svg> draws with <image>
  vp: (s) => <image href={(expansionAssets as Record<string, string>)["tokens/icon-score"]} width={s} height={s} />,
  credit: (s) => <CreditIcon size={s} />,
  energy: (s) => <EnergyIcon size={s} />,
  publicity: (s) => <PublicityIcon size={s} />,
  data: (s) => <DataIcon size={s} />,
  card_any: (s) => <DeckCardIcon size={s} />,
  card: (s) => <DeckCardIcon size={s} />,
};
const NAMES: Record<string, string> = {
  vp: "points",
  credit: "credit",
  energy: "energy",
  publicity: "publicity",
  data: "data",
  card_any: "card",
  card: "card",
};
const PICTURES = (assets as unknown as { anomalyTokens?: Record<string, string> }).anomalyTokens ?? {};
const W = 200; // the picture of a token on the board (264 x 159 pixels, shown at this width)
const R = 70;
const HEX = Array.from({ length: 6 }, (_, k) => {
  const a = (Math.PI / 3) * k + Math.PI / 6;
  return `${(R * Math.cos(a)).toFixed(1)},${(R * Math.sin(a)).toFixed(1)}`;
}).join(" ");

/** `at` is the middle of the token on the board. The reward shows only when the engine says what the token pays. */
export function AnomalyTokenView({ token, at }: { token: AnomalyToken; at: { x: number; y: number } }) {
  const colour = COLORS[token.color] ?? "#ffffff";
  const reward = token.reward ?? [];
  const what = reward.map((r) => `${r.n} ${NAMES[r.t] ?? r.t}`).join(" and ");
  const picture = PICTURES[`${token.color}-${token.side}`];
  if (picture) {
    // the oval lies along the ring (its long side tangent to it), turned so that the reward is not upside down
    let turn = (Math.atan2(at.y - CENTER.y, at.x - CENTER.x) * 180) / Math.PI + 90;
    turn = ((turn % 360) + 360) % 360;
    if (turn > 90 && turn < 270) turn -= 180;
    const h = (W * 159) / 264;
    return (
      <g transform={`translate(${at.x} ${at.y}) rotate(${turn.toFixed(1)})`}>
        <title>{`Anomaly (${token.color}): when Earth reaches this sector, the player with the highest ${token.color} trace gains ${what || "its reward"}`}</title>
        <image href={picture} x={-W / 2} y={-h / 2} width={W} height={h} />
      </g>
    );
  }
  return (
    <g transform={`translate(${at.x} ${at.y})`}>
      <title>{`Anomaly (${token.color}): when Earth reaches this sector, the player with the highest ${token.color} trace gains ${what || "its reward"}`}</title>
      <polygon points={HEX} fill="#10182c" stroke={colour} strokeWidth={9} />
      <polygon points={HEX} fill="none" stroke="#fff" strokeOpacity={0.35} strokeWidth={2} transform="scale(0.86)" />
      {reward.slice(0, 2).map((r, k) => {
        const icon = ICONS[r.t];
        const y = reward.length > 1 ? -34 + k * 40 : -22;
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: at most two entries, in order
          <g key={k} transform={`translate(0 ${y})`}>
            <svg x={-40} y={-18} width={36} height={36} overflow="visible" aria-hidden="true">
              {icon ? icon(36) : null}
            </svg>
            <text x={6} y={11} fontSize={34} fontWeight={700} fill="#fff">
              {r.n > 1 || r.t === "vp" ? `×${r.n}` : ""}
            </text>
          </g>
        );
      })}
      {reward.length <= 1 ? (
        <text y={50} textAnchor="middle" fontSize={22} fill={colour} fontWeight={700}>
          {token.color}
        </text>
      ) : null}
    </g>
  );
}
