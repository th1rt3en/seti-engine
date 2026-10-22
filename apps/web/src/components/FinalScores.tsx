"use client";
// The end of a game: the final scores itemised (the board, the end-of-game cards, the gold tiles, the Exertian cards, the glyphs, the Exertian danger loss),
// who won, the rating change of each rated player, and where to go next. The numbers are those of the engine (`state.final_scores`); this adds nothing.
import { GameStatsPanel } from "@/components/GameStatsPanel";
import { ScoreIcon } from "@/components/Icons";
import type { View } from "@seti/protocol";
import Link from "next/link";
import { useEffect, useState } from "react";
import { playAgainAction } from "../app/actions";
import { PlayerName } from "./PlayerName";

interface RatingChange {
  user_id: string;
  name: string;
  rating_before: number;
  rating_after: number;
  rank: number;
}

export function FinalScores({
  view,
  names,
  gameId,
  gameNum,
  winners,
}: { view: View; names: string[]; gameId: string; gameNum: number; winners: number[] }) {
  const rows = (view.state.final_scores ?? []) as {
    player: number;
    board: number;
    cards: number;
    gold: number;
    exertian: number;
    glyphs?: number;
    loss: number;
    total: number;
    danger?: number;
  }[];
  const [changes, setChanges] = useState<RatingChange[] | null>(null);
  // the Worker writes the ratings a moment after the end: ask a few times
  useEffect(() => {
    let live = true;
    let tries = 0;
    const ask = async () => {
      tries += 1;
      try {
        const res = await fetch(`/api/games/${gameId}/ratings`);
        const body = (await res.json()) as { changes: RatingChange[] };
        if (!live) return;
        if (body.changes.length > 0) {
          setChanges(body.changes);
          return;
        }
      } catch {
        // try again
      }
      if (live && tries < 6) setTimeout(ask, 2000);
    };
    setTimeout(ask, 1500);
    return () => {
      live = false;
    };
  }, [gameId]);
  const who = (i: number): string => (view.state.rival && i === view.state.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  if (rows.length === 0) return null;
  const hasGlyphs = rows.some((r) => (r.glyphs ?? 0) > 0);
  const hasLoss = rows.some((r) => r.loss > 0);
  const hasExertian = rows.some((r) => r.exertian > 0);
  const rating = (name: string) => changes?.find((c) => c.name === name);
  return (
    <div className="finalscores">
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Player</th>
              <th>Board</th>
              <th>End-of-game cards</th>
              <th>Gold tiles</th>
              {hasExertian ? <th>Exertian cards</th> : null}
              {hasGlyphs ? <th>Glyphs</th> : null}
              {hasLoss ? <th>Danger loss</th> : null}
              <th>
                Total <ScoreIcon size={16} />
              </th>
              {changes ? <th>Rating</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const c = rating(names[r.player] ?? "");
              return (
                <tr key={r.player} className={winners.includes(r.player) ? "winner" : undefined}>
                  <td>
                    <PlayerName seat={r.player} name={who(r.player)} />{" "}
                    {winners.includes(r.player) ? <span className="pill">winner</span> : null}
                  </td>
                  <td>{r.board}</td>
                  <td>{r.cards}</td>
                  <td>{r.gold}</td>
                  {hasExertian ? <td>{r.exertian}</td> : null}
                  {hasGlyphs ? <td>{r.glyphs ?? 0}</td> : null}
                  {hasLoss ? <td>{r.loss > 0 ? `−${r.loss}` : 0}</td> : null}
                  <td>
                    <b>{r.total}</b>
                  </td>
                  {changes ? (
                    <td>
                      {c
                        ? `${c.rating_before} → ${c.rating_after} (${c.rating_after - c.rating_before >= 0 ? "+" : ""}${c.rating_after - c.rating_before})`
                        : "—"}
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <GameStatsPanel gameId={gameId} who={who} />
      {view.viewer !== null ? (
        <form action={playAgainAction} className="small">
          <input type="hidden" name="id" value={gameId} />
          <button type="submit" className="primary">
            Play again: a new table with the same settings
          </button>
        </form>
      ) : null}
      <p className="small">
        <Link href={`/replay/${gameNum}`}>Replay the game</Link> · <Link href="/lobby">Back to the lobby</Link> ·{" "}
        <Link href="/leaderboard">Leaderboard</Link>
      </p>
    </div>
  );
}
