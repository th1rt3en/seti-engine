// The quick start cards of the Space Agencies expansion: how often each was kept, and what the players who kept it scored and won. The numbers are the counters
// `quick.<id>` of the engine (stats.py, version 4) with the final score and the win of the player's row.
import { quickText } from "@/lib/moves";
import type { QuickStat } from "@/lib/stats";
import { WithSpread } from "./StatCharts";

const r1 = (x: number): string => (Math.round(x * 10) / 10).toString();
const pct = (x: number): string => `${Math.round(x * 100)}%`;

export function QuickStats({ quick }: { quick: QuickStat[] }) {
  if (quick.length === 0)
    return <p className="muted">No game with quick start cards has been counted yet (it is counted from version 4 of the statistics).</p>;
  return (
    <div className="tablewrap">
      <table className="res-table" aria-label="Quick start cards">
        <thead>
          <tr>
            <th scope="col">Quick start card</th>
            <th scope="col">Kept by</th>
            <th scope="col">Share of players</th>
            <th scope="col">Average final score</th>
            <th scope="col">Won the game</th>
          </tr>
        </thead>
        <tbody>
          {quick.map((q) => (
            <tr key={q.id}>
              <th scope="row">{quickText(q.id)}</th>
              <td>{q.players}</td>
              <td>{pct(q.share)}</td>
              <td>
                <WithSpread spread={q.scoreSpread}>{r1(q.avgScore)}</WithSpread>
              </td>
              <td>{pct(q.winRate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
