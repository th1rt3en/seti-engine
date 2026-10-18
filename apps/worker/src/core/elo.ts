// Elo rating (docs/PLAN.md section 6, decisions D15 and D37).
// 2 players: standard Elo. 3 and 4 players: every pair of players is a matchup; each player's change is the sum over the
// opponents of K / (n - 1) times (actual - expected), so one game moves a rating by at most K.
// A player's K depends on how many rated games they have played: 60 for the first 10, 40 for the next 10, then 20. Everybody starts at 0.
// A rating never drops below 100, and a player who is below 100 does not lose anything by losing (the winner gains as usual).

export const K = 20;
export const START_RATING = 0;
/** No rating drops below this by losing, and a player below it loses nothing. */
export const FLOOR = 100;

/** K for a player with this many rated games played before the game. */
export function kFor(games: number): number {
  return games < 10 ? 60 : games < 20 ? 40 : K;
}

export interface Ranked {
  id: string;
  rating: number;
  /** 1 is the best. Equal ranks are a draw (the rulebook leaves the tie). */
  rank: number;
  /** The rated games the player has played before this one; their K follows from it (`kFor`). Without it K is 20. */
  games?: number;
}

export function expected(ra: number, rb: number): number {
  return 1 / (1 + 10 ** ((rb - ra) / 400));
}

/** The rating change of every player (not rounded, and before the floor; see `applyDeltas`). */
export function deltas(players: Ranked[], k?: number): Map<string, number> {
  const n = players.length;
  const out = new Map<string, number>();
  for (const p of players) {
    const own = k ?? (p.games === undefined ? K : kFor(p.games));
    let sum = 0;
    for (const q of players) {
      if (q === p) continue;
      const actual = p.rank < q.rank ? 1 : p.rank === q.rank ? 0.5 : 0;
      sum += (own / (n - 1)) * (actual - expected(p.rating, q.rating));
    }
    out.set(p.id, sum);
  }
  return out;
}

/** New ratings, rounded to whole points, with the floor: a player below 100 never loses, nobody drops below 100 by losing. */
export function applyDeltas(players: Ranked[], k?: number): Map<string, number> {
  const d = deltas(players, k);
  return new Map(
    players.map((p) => {
      const change = d.get(p.id) ?? 0;
      if (p.rating < FLOOR) return [p.id, change < 0 ? p.rating : Math.round(p.rating + change)];
      return [p.id, Math.max(FLOOR, Math.round(p.rating + change))];
    }),
  );
}
