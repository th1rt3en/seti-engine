// A small line chart of a player's rating over their rated games (server component, plain SVG).
export function RatingChart({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const w = 560;
  const h = 140;
  const pad = 14;
  const lo = Math.min(...points);
  const hi = Math.max(...points);
  const span = Math.max(1, hi - lo);
  const x = (i: number) => pad + (i * (w - 2 * pad)) / (points.length - 1);
  const y = (v: number) => h - pad - ((v - lo) * (h - 2 * pad)) / span;
  const line = points.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1).toFixed(1)} ${h - pad} L${x(0).toFixed(1)} ${h - pad} Z`;
  return (
    <svg
      className="ratingchart"
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={`Rating from ${points[0]} to ${points[points.length - 1]}`}
    >
      <path d={area} className="area" />
      <path d={line} className="line" />
      <circle cx={x(points.length - 1)} cy={y(points[points.length - 1] as number)} r="4" className="dot" />
      <text x={pad} y={12} className="lbl">
        {hi}
      </text>
      <text x={pad} y={h - 2} className="lbl">
        {lo}
      </text>
    </svg>
  );
}
