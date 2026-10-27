"use client";
// The quick start cards of the Space Agencies expansion: how often each was kept, and what the players who kept it scored and won. The numbers are the counters
// `quick.<id>` of the engine (stats.py, version 4) with the final score and the win of the player's row. Every column can be sorted by a click on its head;
// a card is named by its id, and its picture shows on hover (a click on a touch screen: the id is underlined with dashes to say so).
import { cardImage } from "@/lib/cardImages";
import type { QuickStat } from "@/lib/stats";
import { useEffect, useMemo, useState } from "react";
import { WithSpread } from "./StatCharts";

const r1 = (x: number): string => (Math.round(x * 10) / 10).toString();
const pct = (x: number): string => `${Math.round(x * 100)}%`;

type Key = "id" | "keepRate" | "avgScore" | "winRate";
const COLUMNS: { key: Key; label: string }[] = [
  { key: "id", label: "Quick start card" },
  { key: "keepRate", label: "Keep rate" },
  { key: "avgScore", label: "Average final score" },
  { key: "winRate", label: "Win rate" },
];
/** The number of the card ("SR.12" is after "SR.3"). */
const idNumber = (id: string): number => Number(id.split(".")[1] ?? 0);

/** The id of a card, underlined with dashes: the picture of the card shows beside it on hover, or after a click (on a touch screen). */
function CardId({ id }: { id: string }) {
  const [at, setAt] = useState<{ x: number; y: number } | null>(null);
  const src = cardImage(id);
  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    const w = 240;
    const x = Math.max(8, Math.min(r.right + 12, window.innerWidth - w - 8));
    setAt({ x, y: Math.max(8, Math.min(r.top - 40, window.innerHeight - 360)) });
  };
  useEffect(() => {
    if (at === null) return;
    const close = () => setAt(null);
    window.addEventListener("scroll", close, true);
    return () => window.removeEventListener("scroll", close, true);
  }, [at]);
  if (src === undefined) return <>{id}</>;
  return (
    <>
      <button
        type="button"
        className="card-id"
        aria-expanded={at !== null}
        aria-label={`${id}: show the card`}
        onMouseEnter={(e) => matchMedia("(hover: hover)").matches && show(e.currentTarget)}
        onMouseLeave={() => setAt(null)}
        onClick={(e) => (at === null ? show(e.currentTarget) : setAt(null))}
        onBlur={() => setAt(null)}
      >
        {id}
      </button>
      {at !== null ? (
        <img className="card-peek" src={src} alt={`Quick start card ${id}`} width={240} style={{ left: at.x, top: at.y }} />
      ) : null}
    </>
  );
}

export function QuickStats({ quick }: { quick: QuickStat[] }) {
  const [sort, setSort] = useState<{ key: Key; down: boolean }>({ key: "keepRate", down: true });
  const rows = useMemo(() => {
    const value = (q: QuickStat): number => (sort.key === "id" ? idNumber(q.id) : q[sort.key]);
    // a card that nobody kept has no score or win rate: it goes last whichever way the column is sorted
    const empty = (q: QuickStat): boolean => q.players === 0 && (sort.key === "avgScore" || sort.key === "winRate");
    return [...quick].sort(
      (a, b) => Number(empty(a)) - Number(empty(b)) || (value(a) - value(b)) * (sort.down ? -1 : 1) || idNumber(a.id) - idNumber(b.id),
    );
  }, [quick, sort]);
  if (quick.length === 0)
    return <p className="muted">No game with quick start cards has been counted yet (it is counted from version 8 of the statistics).</p>;
  return (
    <div className="tablewrap">
      <table className="res-table" aria-label="Quick start cards">
        <thead>
          <tr>
            {COLUMNS.map((c) => (
              <th key={c.key} scope="col" aria-sort={sort.key === c.key ? (sort.down ? "descending" : "ascending") : "none"}>
                <button
                  type="button"
                  className="sort-head"
                  onClick={() => setSort((s) => ({ key: c.key, down: s.key === c.key ? !s.down : c.key !== "id" }))}
                >
                  {c.label}
                  <span aria-hidden="true">{sort.key === c.key ? (sort.down ? " ▼" : " ▲") : ""}</span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((q) => (
            <tr key={q.id}>
              <th scope="row">
                <CardId id={q.id} />
              </th>
              <td
                title={`Kept ${q.players} time${q.players === 1 ? "" : "s"} out of ${q.offered} time${q.offered === 1 ? "" : "s"} offered`}
              >
                {pct(q.keepRate)} ({q.players})
              </td>
              <td>{q.players === 0 ? "-" : <WithSpread spread={q.scoreSpread}>{r1(q.avgScore)}</WithSpread>}</td>
              <td>{q.players === 0 ? "-" : pct(q.winRate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
