// Statistics of the finished games: the averages of the counters that the engine made for each player of each game (services/engine stats.py, table
// game_stats). Only games that were played to their end are in the table. Nothing here is a rule: it adds up what the engine counted.

/** A player of a finished game, as stored. `eloDelta` is the change of rating of the player in that game (rated games only, else null). */
export interface StatRow {
  gameId: string;
  seat: number;
  userId: string;
  players: number;
  rated: boolean;
  expansion: boolean;
  rank: number;
  won: boolean;
  score: number;
  org: string | null;
  orgOffered: string[];
  species: string[];
  counters: Record<string, number>;
  eloDelta: number | null;
}

/** What the visitor chose to look at; null is "any". */
export interface StatFilter {
  players: number | null;
  expansion: boolean | null;
  rated: boolean | null;
}

const flag = (v: string | undefined): boolean | null => (v === "yes" ? true : v === "no" ? false : null);

export function parseFilter(sp: { players?: string; expansion?: string; rated?: string }): StatFilter {
  const n = Number(sp.players);
  return { players: Number.isInteger(n) && n >= 1 && n <= 4 ? n : null, expansion: flag(sp.expansion), rated: flag(sp.rated) };
}

export const matches = (r: StatRow, f: StatFilter): boolean =>
  (f.players === null || r.players === f.players) &&
  (f.expansion === null || r.expansion === f.expansion) &&
  (f.rated === null || r.rated === f.rated);

export interface OrgStat {
  org: string;
  offered: number;
  picked: number;
  /** picked / offered */
  pickRate: number;
  winRate: number | null;
  /** The mean change of rating of the players who picked it, in the rated games only. */
  eloDelta: number | null;
  eloGames: number;
}

/** How the players differ from the mean: the lowest and the highest value, and the standard deviation (of the players counted, not an estimate). */
export interface Spread {
  min: number;
  max: number;
  std: number;
}

export function spreadOf(values: number[]): Spread {
  if (values.length === 0) return { min: 0, max: 0, std: 0 };
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  return { min: Math.min(...values), max: Math.max(...values), std: Math.sqrt(variance) };
}

export interface SpeciesStat {
  species: string;
  games: number;
  avgScore: number;
  /** of the final scores of the players of those games */
  spread: Spread;
}

export interface GoldStat {
  face: string;
  times: number;
  avgPoints: number;
  /** of the points each time the tile was scored (a player who scored it twice in a game counts twice, with the mean of the two) */
  spread: Spread;
}

export interface TechStat {
  tech: string;
  /** the share of the players who researched it */
  share: number;
}

export interface Stats {
  games: number;
  rows: number;
  /** the mean of every counter over the players (a player without the counter counts as 0) */
  mean: Record<string, number>;
  orgs: OrgStat[];
  species: SpeciesStat[];
  gold: GoldStat[];
  techs: TechStat[];
  /** the rounds that have an income (the expansion has no round 1) */
  rounds: number[];
  /** the players counted (one row each), for the spread of a number that the page works out from the counters */
  players: StatRow[];
  /** the spread of every counter over the players (a player without the counter counts as 0) */
  spread: Record<string, Spread>;
  /** the final scores of the players, lowest first */
  scores: number[];
  /** the mean and the best final score, and the share of the players who won */
  avgScore: number;
  bestScore: number;
  winRate: number;
}

const sum = (xs: number[]): number => xs.reduce((a, b) => a + b, 0);

export function aggregate(all: StatRow[], filter: StatFilter): Stats {
  const rows = all.filter((r) => matches(r, filter));
  const n = rows.length;
  const totals: Record<string, number> = {};
  for (const r of rows) for (const [k, v] of Object.entries(r.counters)) totals[k] = (totals[k] ?? 0) + v;
  const mean: Record<string, number> = {};
  for (const [k, v] of Object.entries(totals)) mean[k] = n === 0 ? 0 : v / n;

  const orgs = new Map<string, { offered: number; picked: number; won: number; elo: number[] }>();
  const slot = (org: string) => {
    let s = orgs.get(org);
    if (!s) {
      s = { offered: 0, picked: 0, won: 0, elo: [] };
      orgs.set(org, s);
    }
    return s;
  };
  for (const r of rows) {
    for (const o of r.orgOffered) slot(o).offered += 1;
    if (r.org) {
      const s = slot(r.org);
      s.picked += 1;
      if (r.won) s.won += 1;
      if (r.eloDelta !== null) s.elo.push(r.eloDelta);
    }
  }

  const species = new Map<string, { games: Set<string>; score: number; rows: number; scores: number[] }>();
  for (const r of rows) {
    for (const sp of r.species) {
      let s = species.get(sp);
      if (!s) {
        s = { games: new Set(), score: 0, rows: 0, scores: [] };
        species.set(sp, s);
      }
      s.games.add(r.gameId);
      s.score += r.score;
      s.rows += 1;
      s.scores.push(r.score);
    }
  }

  const gold: GoldStat[] = [];
  for (const k of Object.keys(totals).filter((k) => k.startsWith("gold.") && k.endsWith(".times"))) {
    const face = k.slice("gold.".length, -".times".length);
    const times = totals[k] ?? 0;
    const each = rows.flatMap((r) => {
      const t = r.counters[`gold.${face}.times`] ?? 0;
      return t > 0 ? Array<number>(t).fill((r.counters[`gold.${face}.points`] ?? 0) / t) : [];
    });
    gold.push({ face, times, avgPoints: times === 0 ? 0 : (totals[`gold.${face}.points`] ?? 0) / times, spread: spreadOf(each) });
  }
  gold.sort((a, b) => a.face.localeCompare(b.face));

  const techs: TechStat[] = Object.keys(totals)
    .filter((k) => k.startsWith("tech."))
    .map((k) => ({ tech: k.slice("tech.".length), share: n === 0 ? 0 : rows.filter((r) => (r.counters[k] ?? 0) > 0).length / n }))
    .sort((a, b) => b.share - a.share);

  const rounds = [
    ...new Set(Object.keys(totals).flatMap((k) => (k.startsWith("incomerate.r") ? [Number(k.split(".")[1]?.slice(1))] : []))),
  ].sort((a, b) => a - b);

  const scores = rows.map((r) => r.score).sort((a, b) => a - b);
  const spread: Record<string, Spread> = {};
  for (const k of Object.keys(totals)) spread[k] = spreadOf(rows.map((r) => r.counters[k] ?? 0));
  return {
    games: new Set(rows.map((r) => r.gameId)).size,
    rows: n,
    players: rows,
    spread,
    scores,
    avgScore: n === 0 ? 0 : sum(scores) / n,
    bestScore: scores.at(-1) ?? 0,
    winRate: n === 0 ? 0 : rows.filter((r) => r.won).length / n,
    mean,
    orgs: [...orgs.entries()]
      .map(([org, s]) => ({
        org,
        offered: s.offered,
        picked: s.picked,
        pickRate: s.offered === 0 ? 0 : s.picked / s.offered,
        winRate: s.picked === 0 ? null : s.won / s.picked,
        eloDelta: s.elo.length === 0 ? null : sum(s.elo) / s.elo.length,
        eloGames: s.elo.length,
      }))
      .sort((a, b) => b.pickRate - a.pickRate),
    species: [...species.entries()]
      .map(([sp, s]) => ({ species: sp, games: s.games.size, avgScore: s.rows === 0 ? 0 : s.score / s.rows, spread: spreadOf(s.scores) }))
      .sort((a, b) => b.avgScore - a.avgScore),
    gold,
    techs,
    rounds,
  };
}
