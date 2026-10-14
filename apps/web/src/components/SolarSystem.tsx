// The solar system drawn from the engine's state: the three discs turned by their angles (the discs are the real pieces, so the planets,
// asteroids and cut-outs show as they are), the probes at their ring and sector, and the sector ring with the nearby stars.
// It computes no rule: where a probe stands and how far a disc is turned are in the state.
import type { GameState } from "@seti/protocol";
import assets from "../generated/assets.json";
import solar from "../generated/solar.json";

const RING_RADIUS = [0, 130, 251, 404, 600]; // the middle of rings 1 to 4, in the units of the disc images
const DISCS: { n: 1 | 2 | 3; size: number }[] = [
  { n: 3, size: 1008 },
  { n: 2, size: 608 },
  { n: 1, size: 396 },
];
const SECTOR_COLORS: Record<string, string> = { yellow: "#d9a400", red: "#d04a3a", blue: "#3b7bd9", black: "#555a63" };
const PLAYER_COLORS: Record<string, string> = { green: "#3fb950", red: "#f85149", purple: "#a371f7", white: "#f0f0f0" };

/** Where sector `s` is: its middle lies 27 + 45 * s degrees counter-clockwise from the east (read from the disc images). */
const spot = (radius: number, sector: number): [number, number] => {
  const a = ((27 + 45 * sector) * Math.PI) / 180;
  return [radius * Math.cos(a), -radius * Math.sin(a)];
};

const arc = (r1: number, r2: number, sector: number): string => {
  const a0 = ((4.5 + 45 * sector) * Math.PI) / 180;
  const a1 = a0 + Math.PI / 4;
  const p = (r: number, a: number): string => `${(r * Math.cos(a)).toFixed(1)} ${(-r * Math.sin(a)).toFixed(1)}`;
  return `M ${p(r1, a0)} A ${r1} ${r1} 0 0 0 ${p(r1, a1)} L ${p(r2, a1)} A ${r2} ${r2} 0 0 1 ${p(r2, a0)} Z`;
};

const ring = (n: number): number => RING_RADIUS[n] ?? 130;

export function SolarSystem({ state, who }: { state: GameState; who: (i: number) => string }) {
  const anomalies = state.species.flatMap((sp) =>
    sp.discovered && sp.species === "anomalies" ? ((sp.extra.tokens as { sector: number; color: string }[] | undefined) ?? []) : [],
  );
  const slotCount = new Map<string, number>();
  return (
    <svg viewBox="-840 -840 1680 1680" className="solar" role="img" aria-label="The solar system">
      <circle r={700} fill="#0b1020" />
      <circle r={700} fill="none" stroke="#243056" strokeWidth={2} />
      {state.sectors.map((sec, i) => {
        const [lx, ly] = spot(750, i);
        const [mx, my] = spot(650, i);
        return (
          <g key={sec.star}>
            <path d={arc(702, 800, i)} fill={SECTOR_COLORS[sec.color] ?? "#444"} opacity={0.85} stroke="#0d1117" strokeWidth={3} />
            <text x={lx} y={ly - 8} fontSize={24} fill="#fff" textAnchor="middle" dominantBaseline="middle" fontWeight={700}>
              {sec.star.length > 14 ? `${sec.star.slice(0, 13)}.` : sec.star}
            </text>
            <text x={lx} y={ly + 20} fontSize={22} fill="#fff" textAnchor="middle" dominantBaseline="middle">
              {`${sec.data_remaining}/${sec.capacity}${sec.markers.length > 0 ? ` · ${sec.markers.length} marked` : ""}`}
            </text>
            <text x={mx} y={my} fontSize={20} fill="#6b7aa8" textAnchor="middle" dominantBaseline="middle">
              {i}
            </text>
          </g>
        );
      })}
      {solar.ring4.map((cell, i) => {
        if (!cell.startsWith("PLANET:")) return null;
        const [x, y] = spot(ring(4), i);
        return (
          <g key={`planet-${cell}`}>
            <circle cx={x} cy={y} r={46} fill="#2e5da8" stroke="#9ec1ff" strokeWidth={3} />
            <text x={x} y={y} fontSize={22} fill="#fff" textAnchor="middle" dominantBaseline="middle">
              {cell.slice(7, 10)}
            </text>
          </g>
        );
      })}
      {DISCS.map(({ n, size }) => (
        <image
          key={n}
          href={(assets.discs as Record<string, string>)[n === 3 && state.oumuamua_placed ? "disc-3-oumuamua" : `disc-${n}`]}
          x={-size / 2}
          y={-size / 2}
          width={size}
          height={size}
          transform={`rotate(${-45 * (state.disc_angles[n - 1] ?? 0)})`}
        />
      ))}
      {anomalies.map((a) => {
        const [x, y] = spot(ring(4), a.sector);
        return (
          <g key={`${a.color}-${a.sector}`}>
            <circle cx={x - 60} cy={y} r={30} fill="#10231d" stroke="#46d9a0" strokeWidth={4} />
            <text x={x - 60} y={y} fontSize={18} fill="#46d9a0" textAnchor="middle" dominantBaseline="middle">
              {a.color.slice(0, 1).toUpperCase()}
            </text>
          </g>
        );
      })}
      {state.probes.map((p) => {
        const key = `${p.ring}-${p.sector}`;
        const k = slotCount.get(key) ?? 0;
        slotCount.set(key, k + 1);
        const [x, y] = spot(ring(p.ring), p.sector);
        const color = PLAYER_COLORS[state.players[p.player]?.color ?? "white"] ?? "#fff";
        const dx = (k % 3) * 30 - 30;
        const dy = Math.floor(k / 3) * 30;
        return (
          <g key={p.id}>
            {p.capsule ? (
              <rect x={x + dx - 14} y={y + dy - 14} width={28} height={28} fill={color} stroke="#000" strokeWidth={3} />
            ) : (
              <circle cx={x + dx} cy={y + dy} r={16} fill={color} stroke="#000" strokeWidth={3} />
            )}
            <title>{`${who(p.player)}: ${p.capsule ? "sample capsule" : "probe"} (ring ${p.ring}, sector ${p.sector})`}</title>
          </g>
        );
      })}
    </svg>
  );
}
