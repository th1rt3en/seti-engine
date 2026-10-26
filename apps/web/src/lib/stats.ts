import { GAIN_RESOURCES } from "./resources";
import { TECH_METRICS, TECH_ORDER } from "./techs";

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

/** What the visitor chose to look at; null is "any". `who` chooses whose numbers count: people only (the AI's rows are left out; the people of a game
 * with an AI still count), the AI only, or everybody. */
export interface StatFilter {
  players: number | null;
  expansion: boolean | null;
  rated: boolean | null;
  who: "people" | "ai" | null;
  /** the games that have at least one of these alien species (discovered or not); none chosen: any */
  species: string[];
  /** the players who picked one of these organizations (the games where it was picked are not otherwise filtered); none chosen: any */
  org: string[];
}

/** The alien species of the game (the engine's names): the five of the base game and the three of the Space Agencies expansion. */
export const SPECIES_KEYS = ["anomalies", "centaurians", "exertians", "mascamites", "oumuamua", "arkhos", "glyphids", "amoeba"];

/** A list in the address: `a,b` (or the name twice), keeping only what `ok` accepts, without repeats, in a fixed order (it is the key of the cache). */
function list(v: string | string[] | undefined, ok: (x: string) => boolean): string[] {
  const all = (Array.isArray(v) ? v : [v ?? ""]).flatMap((x) => x.split(","));
  return [...new Set(all.map((x) => x.trim()).filter((x) => x !== "" && ok(x)))].sort();
}

const flag = (v: string | undefined): boolean | null => (v === "yes" ? true : v === "no" ? false : null);

export function parseFilter(sp: {
  players?: string;
  expansion?: string;
  rated?: string;
  who?: string;
  species?: string | string[];
  org?: string | string[];
}): StatFilter {
  const n = Number(sp.players);
  return {
    players: Number.isInteger(n) && n >= 1 && n <= 4 ? n : null,
    expansion: flag(sp.expansion),
    rated: flag(sp.rated),
    // the default is the people: the games of the AI are looked at on purpose ("ai"), or with everybody ("all")
    who: sp.who === "ai" ? "ai" : sp.who === "all" ? null : "people",
    species: list(sp.species, (x) => SPECIES_KEYS.includes(x)),
    // an organization is a short id of the engine (letters and underscores): anything else is no filter
    org: list(sp.org, (x) => /^[a-z_]{3,40}$/.test(x)),
  };
}

/** A seat of the AI model has the user id `bot:<version>:<n>` (the Worker's room). */
const isAi = (r: StatRow): boolean => r.userId.startsWith("bot:");

export const matches = (r: StatRow, f: StatFilter): boolean =>
  (f.players === null || r.players === f.players) &&
  (f.expansion === null || r.expansion === f.expansion) &&
  (f.rated === null || r.rated === f.rated) &&
  (f.who === null || isAi(r) === (f.who === "ai")) &&
  (f.species.length === 0 || f.species.some((x) => r.species.includes(x))) &&
  (f.org.length === 0 || (r.org !== null && f.org.includes(r.org)));

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
  /** The mean final score of the players who picked it (null when nobody did), and how they differ. */
  avgScore: number | null;
  scoreSpread: Spread;
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

/** What one tech did for the players who have it (the counters `techuse.<tech>.<key>`, mean and spread over those players). */
export interface TechUseStat {
  tech: string;
  /** the players who had the tech at the end of the game */
  players: number;
  /** the share of the players of the rows who researched it (the research percentage) */
  share: number;
  metrics: { key: string; label: string; mean: number; total: number; spread: Spread }[];
}

export interface TechStat {
  tech: string;
  /** the share of the players who researched it */
  share: number;
}

/** The counters that came with the version 2 of the statistics (from effects, what the techs did) exist only in the rows made by it: the games that could not be
 * replayed when they were made again keep the old rows, which would count as zeros. These are worked out over the rows that have the mark. */
export interface FreshStats {
  /** the players whose rows have the counters */
  rows: number;
  mean: Record<string, number>;
  spread: Record<string, Spread>;
}

export const FRESH_VERSION = 2;
/** The version of the statistics that counts the cards played by round and the parts of the final score. */
export const CARDS_VERSION = 3;
/** The version that counts what each resource was spent on and the quick start cards kept. */
export const SPEND_VERSION = 5;
/** The version that counts where each tech came from (the research action, a card of the main deck, an alien card). */
export const TECH_ORIGIN_VERSION = 9;
/** The version that counts the cards that were in a hand and the cards discarded for their free corner (the play rate and the discard rate). */
export const CARD_RATE_VERSION = 10;
/** The version that counts the quick start cards that were offered. */
export const QUICK_VERSION = 8;

/** What a quick start card did for the players who kept it (the counters `quick.<id>`, from version 4). */
export interface QuickStat {
  id: string;
  /** the players who kept it, and the players to whom it was offered (the keep rate is the first over the second) */
  players: number;
  offered: number;
  keepRate: number;
  avgScore: number;
  scoreSpread: Spread;
  winRate: number;
}

/** One slice of a pie: where a resource came from (the mean per player, and how the players differ). */
export interface Slice {
  key: string;
  mean: number;
  spread: Spread;
  /** for a group of sources: what it is made of (the mean per player of each), the largest first */
  parts?: { key: string; mean: number }[];
}

/** The groups of the sources of each resource (the owner's choice for the credits, 2026-10-26; the others are to be reviewed): what is not named is "other".
 * The keys are the kinds of the engine (and the splits of the publicity of moving). */
export const RESOURCE_GROUPS: Record<string, Record<string, string>> = (() => {
  const alien = { alien: "alien", anomaly: "alien", explore: "alien", glyph: "alien", trace: "alien", move_deliver_sample: "alien" };
  const common = { income: "income", organization: "organization", mission: "mission", quick_start: "quick_start", tech: "tech", ...alien };
  return {
    credit: { ...common },
    energy: { ...common, planet: "planet" },
    card: {
      ...common,
      planet: "planet",
      move_take_round_card: "pass",
      move_buy_card: "trade",
      move_exchange: "trade",
      move_org_free: "organization",
      move_org_main: "organization",
    },
    data: {
      ...common,
      signal: "signal",
      planet: "planet",
      move_choose_land_slot: "planet",
      card: "card",
      corner: "corner",
      move_org_free: "organization",
    },
    publicity: {
      ...common,
      visit_comet: "probe",
      visit_asteroid: "probe",
      visit_planet: "probe",
      move_move_probe: "probe",
      move_place_data: "computer",
      move_org_free: "organization",
      sector: "sector",
      planet: "planet",
      card: "card",
      corner: "corner",
    },
    vp: {
      ...common,
      planet: "planet",
      signal: "signal",
      sector: "sector",
      card: "card",
      corner: "corner",
      move_pass: "pass",
      move_place_data: "computer",
    },
    move: { ...common, move_move_energy: "energy", card: "card", corner: "corner", move_org_free: "organization", move_scan_probe: "tech" },
    exofossil: { ...common, planet: "planet", sector: "sector", card: "card" },
    token: {
      glyph_planet: "glyph_planet",
      glyph_tech: "glyph_tech",
      glyph_sector: "glyph_sector",
      glyph_board_lower: "glyph_board_lower",
      glyph_board_upper: "glyph_board_upper",
    },
  };
})();

/** What a card of the main deck or of a species did, over the players who played it (the counters `card.<id>.r<round>`, from version 3). */
export interface CardStat {
  id: string;
  /** the players who played it, and how many times it was played */
  players: number;
  plays: number;
  /** the share of the players of the version 3 rows who played it */
  share: number;
  /** the player-games (of the version 10 rows) in which it was in a hand, and in which it was played and discarded for its free corner: rates are null without them */
  held: number;
  playRate: number | null;
  discardRate: number | null;
  discards: number;
  /** of a mission card: the share of its plays whose mission was completed; of an end-of-game card: the points it gave, per play (null without plays counted) */
  missionRate: number | null;
  endAvg: number | null;
  /** the final score of the players who played it */
  avgScore: number;
  scoreSpread: Spread;
  winRate: number;
  /** the mean round of its plays, and the plays in each round */
  avgRound: number;
  rounds: Record<number, number>;
  /** the organizations of the players who played it, the most frequent first */
  orgs: { org: string; n: number }[];
}

/** The counters of one alien species over the players of the games where it was discovered (the counters `alien.<species>.games` marks them). */
export interface AlienStats {
  rows: number;
  mean: Record<string, number>;
  spread: Record<string, Spread>;
}

export interface Stats {
  /** by resource: where it came from, in slices (the mean per player of each source) */
  gains: Record<string, Slice[]>;
  /** by resource: what it was spent on, in slices (version 4 rows) */
  spends: Record<string, Slice[]>;
  /** the quick start cards that were kept (version 4 rows) */
  quick: QuickStat[];
  /** the cards played, over the rows of version 3 */
  cards: CardStat[];
  /** the rows of version 3 (the cards and the parts of the final score are counted over them) */
  cardRows: number;
  /** by species: what each of them gave and did (see AlienStats) */
  alien: Record<string, AlienStats>;
  /** the counters of version 2 and later, over the rows that have them */
  fresh: FreshStats;
  games: number;
  rows: number;
  /** the mean of every counter over the players (a player without the counter counts as 0) */
  mean: Record<string, number>;
  orgs: OrgStat[];
  species: SpeciesStat[];
  gold: GoldStat[];
  techs: TechStat[];
  /** for each tech, what it did for the players who have it */
  techUse: TechUseStat[];
  /** the techs by type and by where they came from (the mean per player; the origins from version 9 of the statistics) */
  techTypes: Slice[];
  techOrigins: Slice[];
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

  const orgs = new Map<string, { offered: number; picked: number; won: number; elo: number[]; scores: number[] }>();
  const slot = (org: string) => {
    let s = orgs.get(org);
    if (!s) {
      s = { offered: 0, picked: 0, won: 0, elo: [], scores: [] };
      orgs.set(org, s);
    }
    return s;
  };
  for (const r of rows) {
    for (const o of r.orgOffered) slot(o).offered += 1;
    if (r.org) {
      const s = slot(r.org);
      s.picked += 1;
      s.scores.push(r.score);
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

  const fresh = rows.filter((r) => (r.counters["stats.version"] ?? 0) >= FRESH_VERSION);
  const freshTotals: Record<string, number> = {};
  for (const r of fresh) for (const [k, v] of Object.entries(r.counters)) freshTotals[k] = (freshTotals[k] ?? 0) + v;
  const freshMean: Record<string, number> = {};
  for (const [k, v] of Object.entries(freshTotals)) freshMean[k] = fresh.length === 0 ? 0 : v / fresh.length;
  const freshSpread: Record<string, Spread> = {};
  for (const k of Object.keys(freshTotals)) freshSpread[k] = spreadOf(fresh.map((r) => r.counters[k] ?? 0));

  const alien: Record<string, AlienStats> = {};
  for (const sp of SPECIES_KEYS) {
    const mine = rows.filter((r) => (r.counters[`alien.${sp}.games`] ?? 0) > 0);
    const keys = new Set(mine.flatMap((r) => Object.keys(r.counters)));
    const mean: Record<string, number> = {};
    const spreads: Record<string, Spread> = {};
    for (const k of keys) {
      const values = mine.map((r) => r.counters[k] ?? 0);
      mean[k] = sum(values) / values.length;
      spreads[k] = spreadOf(values);
    }
    // everything the species gave, by resource (the parts of its rules added up for each player): `alien.<species>.all.<resource>`
    for (const res of ["vp", "credit", "energy", "card", "publicity", "data", "move", "exofossil", "token"]) {
      const re = new RegExp(`^alien\\.${sp}\\.[a-z_]+\\.${res}$`);
      const values = mine.map((r) =>
        sum(
          Object.entries(r.counters)
            .filter(([k]) => re.test(k) && !k.includes(".all."))
            .map(([, v]) => v),
        ),
      );
      mean[`alien.${sp}.all.${res}`] = values.length === 0 ? 0 : sum(values) / values.length;
      spreads[`alien.${sp}.all.${res}`] = spreadOf(values);
    }
    alien[sp] = { rows: mine.length, mean, spread: spreads };
  }

  const v3 = rows.filter((r) => (r.counters["stats.version"] ?? 0) >= CARDS_VERSION);
  const gains = gainSlices(rows, v3);
  const cards = cardStats(
    v3,
    rows.filter((r) => (r.counters["stats.version"] ?? 0) >= CARD_RATE_VERSION),
  );
  const v4 = rows.filter((r) => (r.counters["stats.version"] ?? 0) >= SPEND_VERSION);
  const spends = spendSlices(v4);
  const quick = quickStats(v4);

  const techUse: TechUseStat[] = TECH_ORDER.map((tech) => {
    const owners = fresh.filter((r) => (r.counters[`tech.${tech}`] ?? 0) > 0);
    return {
      tech,
      players: owners.length,
      share: n === 0 ? 0 : rows.filter((r) => (r.counters[`tech.${tech}`] ?? 0) > 0).length / n,
      metrics: (TECH_METRICS[tech] ?? []).map((m) => {
        const values = owners.map((r) => r.counters[`techuse.${tech}.${m.key}`] ?? 0);
        return { ...m, mean: values.length === 0 ? 0 : sum(values) / values.length, total: sum(values), spread: spreadOf(values) };
      }),
    };
  });

  const meanSlices = (from: StatRow[], keys: string[], prefix: string): Slice[] =>
    keys
      .map((k) => {
        const values = from.map((r) => r.counters[`${prefix}${k}`] ?? 0);
        return { key: k, mean: values.length === 0 ? 0 : sum(values) / values.length, spread: spreadOf(values) };
      })
      .filter((x) => x.mean > 0);
  const techTypes = meanSlices(rows, ["probe", "telescope", "computer"], "techcat.");
  const techOrigins = meanSlices(
    rows.filter((r) => (r.counters["stats.version"] ?? 0) >= TECH_ORIGIN_VERSION),
    ["research", "card", "alien", "other"],
    "techorigin.",
  );

  const rounds = [
    ...new Set(Object.keys(totals).flatMap((k) => (k.startsWith("incomerate.r") ? [Number(k.split(".")[1]?.slice(1))] : []))),
  ].sort((a, b) => a - b);

  const scores = rows.map((r) => r.score).sort((a, b) => a - b);
  const spread: Record<string, Spread> = {};
  for (const k of Object.keys(totals)) spread[k] = spreadOf(rows.map((r) => r.counters[k] ?? 0));
  return {
    gains,
    spends,
    quick,
    cards,
    cardRows: v3.length,
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
        avgScore: s.scores.length === 0 ? null : sum(s.scores) / s.scores.length,
        scoreSpread: spreadOf(s.scores),
      }))
      .sort((a, b) => b.pickRate - a.pickRate),
    species: [...species.entries()]
      .map(([sp, s]) => ({ species: sp, games: s.games.size, avgScore: s.rows === 0 ? 0 : s.score / s.rows, spread: spreadOf(s.scores) }))
      .sort((a, b) => b.avgScore - a.avgScore),
    gold,
    techs,
    techUse,
    techTypes,
    techOrigins,
    fresh: { rows: fresh.length, mean: freshMean, spread: freshSpread },
    alien,
    rounds,
  };
}

/** The sources of each resource. A source is the kind of the scope in which the resource was gained (`gain.<kind>.<resource>`); what the actions and free
 * actions gave is told by action (`gainmove.<action>.<resource>`, the keys `move_<action>`), the publicity of moving a probe by what it moved onto, and the
 * points of the end of the game by the part of the final score they came from. The sources are then put in groups for the resources that have some
 * (RESOURCE_GROUPS). */
function gainSlices(rows: StatRow[], v3: StatRow[]): Record<string, Slice[]> {
  const out: Record<string, Slice[]> = {};
  const slice = (key: string, of: StatRow[], f: (c: Record<string, number>) => number): Slice => {
    const values = of.map((r) => f(r.counters));
    return { key, mean: values.length === 0 ? 0 : sum(values) / values.length, spread: spreadOf(values) };
  };
  const visits = (c: Record<string, number>, names: string[]): number =>
    names.reduce((acc, n) => acc + (c[`publicity.visit.${n}`] ?? 0), 0);
  const planets = (c: Record<string, number>): string[] =>
    Object.keys(c)
      .filter((k) => k.startsWith("publicity.visit."))
      .map((k) => k.slice("publicity.visit.".length))
      .filter((n) => !["comet", "asteroid", "asteroids"].includes(n));
  const allVisits = (c: Record<string, number>): number => visits(c, ["comet", "asteroid", "asteroids", ...planets(c)]);
  for (const res of GAIN_RESOURCES) {
    const kinds = new Set<string>();
    const actions = new Set<string>();
    for (const r of rows) {
      for (const k of Object.keys(r.counters)) {
        const m = /^gain\.([a-z_]+)\.([a-z]+)$/.exec(k);
        if (m && m[2] === res) kinds.add(m[1] as string);
        const a = new RegExp(`^gainmove\.([a-z_]+)\.${res}$`).exec(k);
        if (a) actions.add(a[1] as string);
      }
    }
    const getters = new Map<string, (c: Record<string, number>) => number>();
    for (const kind of [...kinds].sort()) {
      const key = `gain.${kind}.${res}`;
      if (kind !== "move") {
        getters.set(kind, (c) => c[key] ?? 0);
        continue;
      }
      if (res === "publicity") {
        getters.set("visit_comet", (c) => visits(c, ["comet"]));
        getters.set("visit_asteroid", (c) => visits(c, ["asteroid", "asteroids"]));
        getters.set("visit_planet", (c) => visits(c, planets(c)));
      }
      for (const a of actions) {
        const k = `gainmove.${a}.${res}`;
        if (res === "publicity" && a === "move_probe") getters.set("move_move_probe", (c) => Math.max(0, (c[k] ?? 0) - allVisits(c)));
        else getters.set(`move_${a}`, (c) => c[k] ?? 0);
      }
      // what the engine did not tell by action (the rows of older versions)
      getters.set("move", (c) => {
        const told = [...actions].reduce((acc, a) => acc + (c[`gainmove.${a}.${res}`] ?? 0), 0);
        // a row that tells no moves of probes by action has the publicity of the visits inside the total: it is not counted twice
        const visited = res === "publicity" && !(`gainmove.move_probe.${res}` in c) ? allVisits(c) : 0;
        return Math.max(0, (c[key] ?? 0) - told - visited);
      });
    }
    const list = [...getters.entries()].map(([key, f]) => slice(key, rows, f)).filter((x) => x.mean > 0);
    const map = RESOURCE_GROUPS[res];
    const grouped = map ? groupSlices(rows, list, map, getters) : list.sort((a, b) => b.mean - a.mean);
    const finals: Slice[] = [];
    if (res === "vp") {
      for (const part of ["cards", "gold", "exertian", "glyphs"])
        if (v3.some((r) => (r.counters[`final.${part}`] ?? 0) > 0)) finals.push(slice(`final_${part}`, v3, (c) => c[`final.${part}`] ?? 0));
    }
    out[res] = [...grouped, ...finals.filter((x) => x.mean > 0)].sort((a, b) =>
      a.key === "other" ? 1 : b.key === "other" ? -1 : b.mean - a.mean,
    );
  }
  return out;
}

/** The slices of a resource in groups: the mean and the spread are those of the sum of the group for each player. What is not in a group is "other";
 * the parts of a group are on its card. */
function groupSlices(
  rows: StatRow[],
  slices: Slice[],
  groups: Record<string, string>,
  getters: Map<string, (c: Record<string, number>) => number>,
): Slice[] {
  const members = new Map<string, string[]>();
  for (const x of slices) {
    const g = groups[x.key] ?? "other";
    members.set(g, [...(members.get(g) ?? []), x.key]);
  }
  const out: Slice[] = [];
  for (const [group, keys] of members) {
    const values = rows.map((r) => sum(keys.map((k) => getters.get(k)?.(r.counters) ?? 0)));
    const parts = keys
      .map((k) => ({ key: k, mean: slices.find((x) => x.key === k)?.mean ?? 0 }))
      .filter((p) => p.mean > 0)
      .sort((a, b) => b.mean - a.mean);
    out.push({
      key: group === "other" ? "other" : `group_${group}`,
      mean: sum(values) / Math.max(1, values.length),
      spread: spreadOf(values),
      parts,
    });
  }
  return out;
}

/** The cards that were played (any card of the main deck or of a species), by what the players who played them scored, won and did. */
function cardStats(v3: StatRow[], v10: StatRow[]): CardStat[] {
  const byCard = new Map<string, { rows: StatRow[]; plays: number; rounds: Record<number, number> }>();
  for (const r of v3) {
    for (const [k, v] of Object.entries(r.counters)) {
      const m = /^card\.(.+)\.r(\d+)$/.exec(k);
      if (!m) continue;
      const id = m[1] as string;
      let e = byCard.get(id);
      if (!e) {
        e = { rows: [], plays: 0, rounds: {} };
        byCard.set(id, e);
      }
      if (e.rows[e.rows.length - 1] !== r) e.rows.push(r);
      e.plays += v;
      e.rounds[Number(m[2])] = (e.rounds[Number(m[2])] ?? 0) + v;
    }
  }
  const held = new Map<string, { held: number; played: number; discards: number; completed: number; endPoints: number }>();
  for (const r of v10) {
    for (const [k, v] of Object.entries(r.counters)) {
      const m = /^cardheld\.(.+)$/.exec(k);
      if (!m || v <= 0) continue;
      const id = m[1] as string;
      const e = held.get(id) ?? { held: 0, played: 0, discards: 0, completed: 0, endPoints: 0 };
      e.held += v;
      for (const [k2, v2] of Object.entries(r.counters)) if (k2.startsWith(`card.${id}.r`)) e.played += v2;
      e.discards += r.counters[`cardcorner.${id}`] ?? 0;
      e.completed += r.counters[`cardmission.${id}`] ?? 0;
      e.endPoints += r.counters[`cardend.${id}`] ?? 0;
      held.set(id, e);
    }
  }
  for (const id of held.keys()) if (!byCard.has(id)) byCard.set(id, { rows: [], plays: 0, rounds: {} });
  return [...byCard.entries()]
    .map(([id, e]) => {
      const h = held.get(id);
      const scores = e.rows.map((r) => r.score);
      const orgs = new Map<string, number>();
      for (const r of e.rows) if (r.org) orgs.set(r.org, (orgs.get(r.org) ?? 0) + 1);
      const rounds = Object.entries(e.rounds);
      return {
        id,
        players: e.rows.length,
        plays: e.plays,
        share: v3.length === 0 ? 0 : e.rows.length / v3.length,
        held: h?.held ?? 0,
        playRate: h && h.held > 0 ? h.played / h.held : null,
        discardRate: h && h.held > 0 ? h.discards / h.held : null,
        discards: h?.discards ?? 0,
        missionRate: h && h.played > 0 ? h.completed / h.played : null,
        endAvg: h && h.played > 0 ? h.endPoints / h.played : null,
        avgScore: scores.length === 0 ? 0 : sum(scores) / scores.length,
        scoreSpread: spreadOf(scores),
        winRate: e.rows.length === 0 ? 0 : e.rows.filter((r) => r.won).length / e.rows.length,
        avgRound: e.plays === 0 ? 0 : sum(rounds.map(([r, n]) => Number(r) * n)) / e.plays,
        rounds: e.rounds,
        orgs: [...orgs.entries()].map(([org, n]) => ({ org, n })).sort((a, b) => b.n - a.n),
      };
    })
    .sort((a, b) => b.plays - a.plays);
}

/** What each resource was spent on: the counters `spend.<what>.<resource>`, the mean per player of the rows that have them. */
function spendSlices(v4: StatRow[]): Record<string, Slice[]> {
  const out: Record<string, Slice[]> = {};
  for (const res of GAIN_RESOURCES) {
    const whats = new Set<string>();
    for (const r of v4) {
      for (const k of Object.keys(r.counters)) {
        const m = /^spend\.([a-z_]+)\.([a-z]+)$/.exec(k);
        if (m && m[2] === res) whats.add(m[1] as string);
      }
    }
    out[res] = [...whats]
      .map((what) => {
        const values = v4.map((r) => r.counters[`spend.${what}.${res}`] ?? 0);
        return { key: what, mean: values.length === 0 ? 0 : sum(values) / values.length, spread: spreadOf(values) };
      })
      .filter((x) => x.mean > 0)
      .sort((a, b) => b.mean - a.mean);
  }
  return out;
}

/** The quick start cards that the players kept, by what those players scored and how often they won. */
function quickStats(v4: StatRow[]): QuickStat[] {
  // the rows that know what was offered (version 8): a card that was offered and never kept has a keep rate of 0
  const rows = v4.filter((r) => (r.counters["stats.version"] ?? 0) >= QUICK_VERSION);
  const offered = new Map<string, StatRow[]>();
  for (const r of rows)
    for (const k of Object.keys(r.counters))
      if (k.startsWith("quickoffered."))
        offered.set(k.slice("quickoffered.".length), [...(offered.get(k.slice("quickoffered.".length)) ?? []), r]);
  return [...offered.entries()]
    .map(([id, offers]) => {
      const kept = offers.filter((r) => (r.counters[`quick.${id}`] ?? 0) > 0);
      const scores = kept.map((r) => r.score);
      return {
        id,
        players: kept.length,
        offered: offers.length,
        keepRate: kept.length / offers.length,
        avgScore: kept.length === 0 ? 0 : sum(scores) / scores.length,
        scoreSpread: spreadOf(scores),
        winRate: kept.length === 0 ? 0 : kept.filter((r) => r.won).length / kept.length,
      };
    })
    .sort((a, b) => b.keepRate - a.keepRate || b.offered - a.offered || a.id.localeCompare(b.id));
}
