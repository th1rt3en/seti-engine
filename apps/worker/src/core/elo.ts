// Elo rating, K = 20 (docs/PLAN.md section 6, decision D15).
// 2 players: standard Elo. 3 and 4 players: every pair of players is a matchup; each player's change is the sum over the
// opponents of K / (n - 1) times (actual - expected), so one game moves a rating by at most K.

export const K = 20;
export const START_RATING = 1500;

export interface Ranked {
  id: string;
  rating: number;
  /** 1 is the best. Equal ranks are a draw (the rulebook leaves the tie). */
  rank: number;
}

export function expected(ra: number, rb: number): number {
  return 1 / (1 + 10 ** ((rb - ra) / 400));
}

/** The rating change of every player (not rounded; see `applyDeltas`). */
export function deltas(players: Ranked[], k: number = K): Map<string, number> {
  const n = players.length;
  const out = new Map<string, number>();
  for (const p of players) {
    let sum = 0;
    for (const q of players) {
      if (q === p) continue;
      const actual = p.rank < q.rank ? 1 : p.rank === q.rank ? 0.5 : 0;
      sum += (k / (n - 1)) * (actual - expected(p.rating, q.rating));
    }
    out.set(p.id, sum);
  }
  return out;
}

/** New ratings, rounded to whole points. */
export function applyDeltas(players: Ranked[], k: number = K): Map<string, number> {
  const d = deltas(players, k);
  return new Map(players.map((p) => [p.id, Math.round(p.rating + (d.get(p.id) ?? 0))]));
}
