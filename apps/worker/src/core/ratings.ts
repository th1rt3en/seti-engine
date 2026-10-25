// What a finished game does to the ratings (docs/PLAN.md section 6): pure, so the D1 sink and the tests share it.
import { START_RATING, applyDeltas } from "./elo.js";
import type { GameRecord } from "./room.js";

export interface RatingUpdate {
  userId: string;
  seat: number;
  rank: number;
  before: number;
  after: number;
}

/** The new ratings of the players of a game; empty when the game does not count (guests, solo, too short). */
export function settle(rec: GameRecord, current: ReadonlyMap<string, { rating: number; games: number }>): RatingUpdate[] {
  if (!rec.rated || rec.meta.seats.some((who) => who?.bot)) return []; // a game with an AI is never rated
  const seats = rec.meta.seats;
  const players = rec.result.ranking.map((r) => {
    const who = seats[r.seat];
    if (who === null || who === undefined) throw new Error(`seat ${r.seat} is empty`);
    const known = current.get(who.id);
    return { id: who.id, seat: r.seat, rank: r.rank, rating: known?.rating ?? START_RATING, games: known?.games ?? 0 };
  });
  const after = applyDeltas(players);
  return players.map((p) => ({ userId: p.id, seat: p.seat, rank: p.rank, before: p.rating, after: after.get(p.id) ?? p.rating }));
}
