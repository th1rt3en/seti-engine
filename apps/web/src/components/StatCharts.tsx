// The pieces of the statistics page: stat tiles, panels, bars, a stacked bar, a histogram and a line chart. They are drawn on the server (HTML and SVG,
// no script): a bar or a point says what it is when the pointer rests on it (the title), and every panel can show its numbers as a table.
// The colours are the validated categorical colours of the dark surface (seti-engine docs: dataviz), set in ui.css as --viz-1 ... --viz-5.
import type { Spread } from "@/lib/stats";
import type { ReactNode } from "react";

/** The lowest value, the highest and the standard deviation of the players, as a small card that opens when the pointer rests on the number (or it has the focus). */
export function SpreadTip({ spread, unit }: { spread: Spread; unit?: string }) {
  return (
    <span className="tip" role="tooltip">
      <span className="tip-head">Players differ</span>
      <span className="tip-grid">
        <span>Lowest</span>
        <b>{round(spread.min)}</b>
        <span>Highest</span>
        <b>{round(spread.max)}</b>
        <span>Std. deviation</span>
        <b>{round(spread.std)}</b>
      </span>
      {unit ? <span className="tip-foot">{unit}</span> : null}
    </span>
  );
}

/** A number with its spread behind it: hovering or focusing it opens the card. */
export function WithSpread({ children, spread }: { children: ReactNode; spread?: Spread }) {
  if (!spread) return <>{children}</>;
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: the card opens when the number has the focus (a keyboard has no hover)
    <span className="has-tip" tabIndex={0}>
      {children}
      <SpreadTip spread={spread} />
    </span>
  );
}

/** A number with its name and an icon: the headline figures. */
export function Tile({
  icon,
  label,
  value,
  note,
  spread,
}: { icon?: ReactNode; label: string; value: ReactNode; note?: string; spread?: Spread }) {
  return (
    <div className="stat-tile">
      {icon ? <span className="stat-tile-icon">{icon}</span> : null}
      <span className="stat-tile-value">
        <WithSpread spread={spread}>{value}</WithSpread>
      </span>
      <span className="stat-tile-label">{label}</span>
      {note ? <span className="stat-tile-note">{note}</span> : null}
    </div>
  );
}

/** A block of the page with a title (and an icon), what it shows, and the same numbers as a table behind a button. */
export function Panel({
  title,
  icon,
  note,
  children,
  table,
  wide,
}: { title: string; icon?: ReactNode; note?: string; children: ReactNode; table?: ReactNode; wide?: boolean }) {
  return (
    <section className={wide ? "card stat-panel wide" : "card stat-panel"}>
      <h2>
        {icon ? <span className="stat-h-icon">{icon}</span> : null}
        {title}
      </h2>
      {note ? <p className="muted small">{note}</p> : null}
      {children}
      {table ? (
        <details className="stat-table">
          <summary>Show as a table</summary>
          {table}
        </details>
      ) : null}
    </section>
  );
}

export interface BarRow {
  key: string;
  label: ReactNode;
  value: number;
  /** what is written at the end of the bar */
  text: ReactNode;
  /** what the pointer shows when it rests on the row */
  title?: string;
  /** how the players differ: shown on a card when the pointer rests on the value */
  spread?: Spread;
  color?: string;
  /** a dark colour needs a light edge to be seen on the dark surface */
  outline?: boolean;
}

/** Horizontal bars with the names at the left and the values at the end, all on one scale (`max`, or the largest value). */
export function BarList({ rows, max, label }: { rows: BarRow[]; max?: number; label: string }) {
  const top = max ?? Math.max(0, ...rows.map((r) => r.value));
  return (
    <ul className="barlist" aria-label={label}>
      {rows.map((r) => (
        // the three columns are shared by all the rows (display: contents), so that every bar has the same length for the same value
        <li key={r.key} className="bar-row">
          <span className="bar-label" title={r.title}>
            {r.label}
          </span>
          <span className="bar-track" title={r.title}>
            <span
              className={r.outline ? "bar-fill outlined" : "bar-fill"}
              style={{
                width: `${top <= 0 ? 0 : Math.max(r.value > 0 ? 1.5 : 0, (r.value / top) * 100)}%`,
                background: r.color ?? "var(--viz-1)",
              }}
            />
          </span>
          <span className="bar-value">
            <WithSpread spread={r.spread}>{r.text}</WithSpread>
          </span>
        </li>
      ))}
    </ul>
  );
}

export interface StackPart {
  key: string;
  label: string;
  icon?: ReactNode;
  value: number;
  color: string;
  spread?: Spread;
}

/** One bar cut into parts (with a gap between them), and under it a legend with every part's value and share. */
export function StackBar({ parts, unit, label }: { parts: StackPart[]; unit?: string; label: string }) {
  const total = parts.reduce((a, p) => a + p.value, 0);
  return (
    <div className="stack">
      <div className="stack-bar" role="img" aria-label={label}>
        {parts
          .filter((p) => p.value > 0)
          .map((p) => (
            <span
              key={p.key}
              className="stack-seg"
              style={{ flexGrow: p.value, background: p.color }}
              title={`${p.label}: ${round(p.value)}${unit ? ` ${unit}` : ""} (${Math.round((p.value / total) * 100)}%)`}
            />
          ))}
      </div>
      <ul className="stack-legend">
        {parts.map((p) => (
          <li key={p.key}>
            <span className="vswatch" style={{ background: p.color }} />
            {p.icon}
            <span className="stack-name">{p.label}</span>
            <b>
              <WithSpread spread={p.spread}>{round(p.value)}</WithSpread>
            </b>
            <span className="muted small">{total > 0 ? `${Math.round((p.value / total) * 100)}%` : ""}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export const round = (x: number): string => (Math.round(x * 10) / 10).toString();

const SURFACE = "var(--panel)";

/** How many players ended with a score in each band of `bin` points (columns, 2 px apart, rounded at the top). */
export function Histogram({ values, bin = 25, label }: { values: number[]; bin?: number; label: string }) {
  const W = 640;
  const H = 220;
  const L = 36;
  const R = 8;
  const T = 12;
  const B = 30;
  const top = Math.max(bin, Math.ceil((Math.max(0, ...values) + 1) / bin) * bin);
  const bins = Array.from({ length: top / bin }, (_, i) => values.filter((v) => v >= i * bin && v < (i + 1) * bin).length);
  const maxCount = Math.max(1, ...bins);
  const yTop = maxCount <= 4 ? maxCount : Math.ceil(maxCount / 4) * 4;
  const step = (W - L - R) / bins.length;
  const y = (c: number): number => T + (H - T - B) * (1 - c / yTop);
  const ticks = yTop <= 4 ? Array.from({ length: yTop + 1 }, (_, i) => i) : [0, yTop / 4, yTop / 2, (yTop * 3) / 4, yTop];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={label}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="vgrid" />
          <text x={L - 6} y={y(t) + 4} textAnchor="end" className="vaxis">
            {t}
          </text>
        </g>
      ))}
      {bins.map((c, i) => {
        const x = L + i * step + 1;
        const w = Math.max(2, step - 2);
        const h = (H - T - B) * (c / yTop);
        const lo = i * bin;
        const name = `${lo} to ${lo + bin - 1} points: ${c} player${c === 1 ? "" : "s"}`;
        return (
          // biome-ignore lint/suspicious/noArrayIndexKey: the bands are in order and never change
          <g key={i}>
            {c > 0 ? <path d={roundedTop(x, y(c), w, h, 4)} fill="var(--viz-1)" /> : null}
            <rect x={L + i * step} y={T} width={step} height={H - T - B} fill="transparent">
              <title>{name}</title>
            </rect>
            {i % Math.ceil(bins.length / 12) === 0 ? (
              <text x={L + i * step} y={H - 10} className="vaxis" textAnchor="start">
                {lo}
              </text>
            ) : null}
          </g>
        );
      })}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} className="vaxisline" />
    </svg>
  );
}

/** A column with a rounded top and a flat foot. */
function roundedTop(x: number, y: number, w: number, h: number, r: number): string {
  const rr = Math.min(r, w / 2, h);
  return `M${x} ${y + h} V${y + rr} Q${x} ${y} ${x + rr} ${y} H${x + w - rr} Q${x + w} ${y} ${x + w} ${y + rr} V${y + h} Z`;
}

export interface LineSeries {
  key: string;
  label: string;
  color: string;
  icon?: ReactNode;
  values: number[];
  /** how the players differ at each point (the same order as `values`) */
  spreads?: Spread[];
}

/** Lines over a few categories (the rounds): 2 px lines, 5 px markers with a ring of the surface colour, the name of the line at its end. */
export function LineChart({ xs, series, label, xName }: { xs: string[]; series: LineSeries[]; label: string; xName: string }) {
  const W = 640;
  const H = 280;
  const L = 40;
  const R = 96;
  const T = 14;
  const B = 34;
  const maxV = Math.max(1, ...series.flatMap((s) => s.values));
  const yTop = niceCeil(maxV);
  const y = (v: number): number => T + (H - T - B) * (1 - v / yTop);
  const x = (i: number): number => (xs.length === 1 ? L + (W - L - R) / 2 : L + ((W - L - R) * i) / (xs.length - 1));
  const ticks = [0, yTop / 4, yTop / 2, (yTop * 3) / 4, yTop];
  return (
    <div>
      <ul className="line-legend">
        {series.map((s) => (
          <li key={s.key}>
            <span className="vswatch round" style={{ background: s.color }} />
            {s.icon}
            {s.label}
          </li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={label}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="vgrid" />
            <text x={L - 6} y={y(t) + 4} textAnchor="end" className="vaxis">
              {round(t)}
            </text>
          </g>
        ))}
        {xs.map((name, i) => (
          <text key={name} x={x(i)} y={H - 12} textAnchor="middle" className="vaxis">
            {xName} {name}
          </text>
        ))}
        {series.map((s) => (
          <g key={s.key}>
            <polyline
              points={s.values.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
              fill="none"
              stroke={s.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {s.values.map((v, i) => (
              <g key={xs[i]}>
                <circle cx={x(i)} cy={y(v)} r={5} fill={s.color} stroke={SURFACE} strokeWidth={2} />
                <circle cx={x(i)} cy={y(v)} r={15} fill="transparent">
                  <title>{pointTitle(s, i, xName, xs[i] ?? "", v)}</title>
                </circle>
              </g>
            ))}
            {s.values.length > 0 ? (
              <text x={x(s.values.length - 1) + 12} y={y(s.values[s.values.length - 1] ?? 0) + 4} className="linelabel">
                {s.label}
              </text>
            ) : null}
          </g>
        ))}
        <line x1={L} x2={W - R} y1={H - B} y2={H - B} className="vaxisline" />
      </svg>
    </div>
  );
}

/** What a point says when the pointer rests on it: its value and, when known, how the players differ. */
function pointTitle(s: LineSeries, i: number, xName: string, x: string, v: number): string {
  const sp = s.spreads?.[i];
  const head = `${s.label}, ${xName.toLowerCase()} ${x}: ${round(v)}`;
  return sp ? `${head} (lowest ${round(sp.min)}, highest ${round(sp.max)}, std. deviation ${round(sp.std)})` : head;
}

function niceCeil(v: number): number {
  const steps = [1, 2, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 150, 200, 300, 400, 500, 1000];
  return steps.find((s) => s >= v) ?? Math.ceil(v / 100) * 100;
}

/** The choices of one filter as links (no script): the current one is marked, the others keep the other filters as they are. */
export function Pills({
  name,
  choices,
  current,
  base,
}: { name: string; choices: { value: string; label: string }[]; current: string; base: Record<string, string> }) {
  const href = (value: string): string => {
    const q = new URLSearchParams({ ...base, ...(value === "" ? {} : { [name]: value }) });
    if (value === "") q.delete(name);
    const s = q.toString();
    return s === "" ? "/stats" : `/stats?${s}`;
  };
  return (
    <nav className="fpills" aria-label={name}>
      {choices.map((c) => (
        <a
          key={c.value}
          href={href(c.value)}
          className={c.value === current ? "fpill on" : "fpill"}
          aria-current={c.value === current ? "true" : undefined}
        >
          {c.label}
        </a>
      ))}
    </nav>
  );
}
