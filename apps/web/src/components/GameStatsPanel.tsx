"use client";
// The statistics of the game that has just ended, under the final scores: what each player did (the counters of the engine, stats.py). They arrive a
// moment after the end, because the engine counts them from a replay of the game; a game that was not played to its end has none.
import { type Counters, statGroups } from "@/lib/gameStatRows";
import { useEffect, useState } from "react";

export function GameStatsPanel({ gameId, who }: { gameId: string; who: (seat: number) => string }) {
  const [players, setPlayers] = useState<{ seat: number; counters: Counters }[] | null>(null);
  const [gaveUp, setGaveUp] = useState(false);
  useEffect(() => {
    let live = true;
    let tries = 0;
    const ask = async () => {
      tries += 1;
      try {
        const res = await fetch(`/api/games/${gameId}/stats`);
        const body = (await res.json()) as { players: { seat: number; counters: Counters }[] };
        if (!live) return;
        if (body.players.length > 0) {
          setPlayers(body.players);
          return;
        }
      } catch {
        // try again
      }
      if (!live) return;
      if (tries < 8) setTimeout(ask, 3000);
      else setGaveUp(true);
    };
    setTimeout(ask, 2000);
    return () => {
      live = false;
    };
  }, [gameId]);
  if (gaveUp) return null;
  if (players === null) return <p className="muted small">Counting the statistics of this game...</p>;
  const groups = statGroups(players.map((p) => p.counters));
  return (
    <details className="gamestats" open>
      <summary>Statistics of this game</summary>
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>&nbsp;</th>
              {players.map((p) => (
                <th key={p.seat}>{who(p.seat)}</th>
              ))}
            </tr>
          </thead>
          {groups.map((g) => (
            <tbody key={g.title}>
              <tr className="statgroup">
                <th colSpan={players.length + 1}>{g.title}</th>
              </tr>
              {g.lines.map((l) => (
                <tr key={`${g.title}-${l.label}`}>
                  <td>{l.label}</td>
                  {players.map((p) => (
                    <td key={p.seat}>{l.value(p.counters)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          ))}
        </table>
      </div>
    </details>
  );
}
