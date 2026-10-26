"use client";
// A pie of the statistics: the slices are what a resource (or a total) is made of, each with the mean per player. Pointing at a slice, or at its row of the
// legend (or giving it the focus), opens a card with the mean, its share and how the players differ (the lowest, the highest, the standard deviation).
// The legend names every slice, so that no slice is known by its color alone.
import type { Spread } from "@/lib/stats";
import { type ReactNode, useState } from "react";

export interface PieSlice {
  key: string;
  label: ReactNode;
  /** the text of the card when the pointer is on the slice (the name, without markup) */
  name: string;
  value: number;
  color: string;
  /** how the players differ (absent for a slice that is a sum of other slices) */
  spread?: Spread;
}

const SIZE = 220;
const R = 100;
const C = SIZE / 2;

const round = (x: number): string => (Math.abs(x) >= 100 ? String(Math.round(x)) : (Math.round(x * 10) / 10).toString());

/** The path of a slice from angle `a0` to `a1` (radians, clockwise from the top). */
function arc(a0: number, a1: number): string {
  const p = (a: number): string => `${(C + R * Math.sin(a)).toFixed(2)} ${(C - R * Math.cos(a)).toFixed(2)}`;
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${C} ${C} L ${p(a0)} A ${R} ${R} 0 ${large} 1 ${p(a1)} Z`;
}

export function PieChart({ slices, label, unit = "per player" }: { slices: PieSlice[]; label: string; unit?: string }) {
  const [on, setOn] = useState<string | null>(null);
  const total = slices.reduce((a, s) => a + s.value, 0);
  if (total <= 0) return <p className="muted">Nothing was gained yet.</p>;
  let at = 0;
  const parts = slices.map((s) => {
    const a0 = at;
    at += (s.value / total) * Math.PI * 2;
    return { s, a0, a1: at };
  });
  const active = slices.find((s) => s.key === on);
  return (
    <div className="pie">
      <div className="pie-art">
        <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label={label} onMouseLeave={() => setOn(null)}>
          {parts.length === 1 ? (
            <circle
              cx={C}
              cy={C}
              r={R}
              fill={(parts[0] as { s: PieSlice }).s.color}
              onMouseEnter={() => setOn((parts[0] as { s: PieSlice }).s.key)}
            />
          ) : (
            parts.map(({ s, a0, a1 }) => (
              <path
                key={s.key}
                d={arc(a0, a1 - 0.0001)}
                fill={s.color}
                stroke="var(--panel, #161b22)"
                strokeWidth={2}
                opacity={on === null || on === s.key ? 1 : 0.45}
                onMouseEnter={() => setOn(s.key)}
                onFocus={() => setOn(s.key)}
                onBlur={() => setOn(null)}
                tabIndex={0}
                aria-label={`${s.name}: ${round(s.value)} ${unit}`}
              />
            ))
          )}
        </svg>
        {active ? (
          <div className="pie-tip" role="tooltip">
            <b>{active.name}</b>
            <span className="tip-grid">
              <span>Average</span>
              <b>
                {round(active.value)} ({Math.round((active.value / total) * 100)}%)
              </b>
              {active.spread ? (
                <>
                  <span>Lowest</span>
                  <b>{round(active.spread.min)}</b>
                  <span>Highest</span>
                  <b>{round(active.spread.max)}</b>
                  <span>Std. deviation</span>
                  <b>{round(active.spread.std)}</b>
                </>
              ) : null}
            </span>
            <span className="tip-foot">{unit}</span>
          </div>
        ) : null}
      </div>
      <ul className="pie-legend">
        {slices.map((s) => (
          <li key={s.key} className={on === s.key ? "on" : undefined} onMouseEnter={() => setOn(s.key)} onMouseLeave={() => setOn(null)}>
            <span className="swatch" style={{ background: s.color }} />
            <span className="pie-name">{s.label}</span>
            <b>{round(s.value)}</b>
            <span className="muted small">{Math.round((s.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
