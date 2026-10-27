// The summary of the statistics, made once for each change of the table and kept (docs/stats-scaling.md). The page used to read every row of `game_stats` and work the
// averages out again whenever its isolate had not seen the current table: about 100 ms of CPU for 100 rows, during which the isolate serves nothing else. Now:
//   1. one cheap question gives the version of the table: the highest rowid of `game_stats` (every write, a game that ends or a backfill with INSERT OR REPLACE,
//      gives its row a new, higher id);
//   2. the summary of the filter is read from the table `stats_summary` (D1), in parts: only the parts that the tab shows;
//   3. only when the summary of that version is not there is it worked out from the rows, and then all its parts are stored;
//   4. the isolate keeps what it read, for as long as the table does not change.
// Without the table `stats_summary` (the migration 0009 is not applied yet) or when D1 fails, it works as before: the summary is worked out in the isolate.
import type { Db } from "./db";
import { statRows } from "./queries";
import { SPECIES_KEYS, type StatFilter, type Stats, aggregate, matches } from "./stats";
import type { StatRow } from "./stats";

/** Change it whenever `aggregate` gives other numbers or another shape: the summaries that were stored by the older code are then not read. */
export const SUMMARY_SHAPE = 1;

/** The most filters kept in the isolate for one version of the table. A summary is about 1 MB of objects and a Worker has 128 MB for everything (error 1102). */
const MAX_SUMMARIES = 12;

/** What the tab asks for besides the core of the summary: the cards (the tab "Others") and the species (the tab "Aliens"). */
export interface Need {
  cards: boolean;
  alien: boolean;
}

const ALL_PARTS: Need = { cards: true, alien: true };

interface Memo {
  version: number;
  rows: StatRow[] | null;
  /** by filter: the parts that were read or made, by name */
  summaries: Map<string, Map<string, unknown>>;
}

let memo: Memo | null = null;

/** Forget everything (tests; a deploy starts with an empty cache anyway). */
export function clearStatsCache(): void {
  memo = null;
}

/** The version of the table: it changes whenever a row is written. */
export async function statsVersion(db: Db): Promise<number> {
  const r = await db.all<{ v: number }>("SELECT COALESCE(MAX(rowid), 0) AS v FROM game_stats");
  return r[0]?.v ?? 0;
}

const ALL: StatFilter = { players: null, expansion: null, rated: null, who: null, species: [], org: [] };

const alienPart = (sp: string): string => `alien:${sp}`;

/** The fields of the summary that are stored apart from the core; the rest is the core. `players` are the rows themselves and are not stored. */
function split(stats: Stats): Map<string, unknown> {
  const { alien, cards, fresh, players: _rows, ...core } = stats;
  const parts = new Map<string, unknown>([
    ["core", core],
    ["fresh", fresh],
    ["cards", cards],
  ]);
  for (const [sp, a] of Object.entries(alien)) parts.set(alienPart(sp), a);
  return parts;
}

/** The names of the parts that a tab reads. */
function wanted(need: Need): string[] {
  return ["core", "fresh", ...(need.cards ? ["cards"] : []), ...(need.alien ? SPECIES_KEYS.map(alienPart) : [])];
}

/** The summary from its parts. A part that was not asked for is empty (a tab does not read it). */
function join(parts: Map<string, unknown>, players: StatRow[]): Stats {
  const alien: Stats["alien"] = {};
  for (const sp of SPECIES_KEYS) {
    const a = parts.get(alienPart(sp)) as Stats["alien"][string] | undefined;
    if (a) alien[sp] = a;
  }
  return {
    ...(parts.get("core") as Omit<Stats, "alien" | "cards" | "fresh" | "players">),
    fresh: (parts.get("fresh") as Stats["fresh"] | undefined) ?? { rows: 0, mean: {}, spread: {} },
    cards: (parts.get("cards") as Stats["cards"] | undefined) ?? [],
    alien,
    players,
  };
}

async function readParts(db: Db, key: string, version: number, names: string[]): Promise<Map<string, unknown>> {
  const out = new Map<string, unknown>();
  if (names.length === 0) return out;
  try {
    const rows = await db.all<{ part: string; json: string }>(
      `SELECT part, json FROM stats_summary WHERE filter_key = ? AND version = ? AND part IN (${names.map(() => "?").join(", ")})`,
      key,
      version,
      ...names,
    );
    for (const r of rows) out.set(r.part, JSON.parse(r.json));
  } catch {
    // no table yet, or D1 failed: the summary is worked out here
  }
  return out;
}

async function storeParts(db: Db, key: string, version: number, parts: Map<string, unknown>): Promise<void> {
  try {
    for (const [part, value] of parts)
      await db.run(
        "INSERT OR REPLACE INTO stats_summary (filter_key, part, version, json) VALUES (?, ?, ?, ?)",
        key,
        part,
        version,
        JSON.stringify(value),
      );
    await db.run("DELETE FROM stats_summary WHERE version < ?", version); // the summaries of the older tables are of no use
  } catch {
    // the summary is kept in the isolate only
  }
}

/** The summary for a filter: from the isolate, else from the table `stats_summary`, else made from the rows (and then stored). */
export async function cachedStats(db: Db, filter: StatFilter, need: Need = ALL_PARTS): Promise<Stats> {
  const version = await statsVersion(db);
  if (memo === null || memo.version !== version) memo = { version, rows: null, summaries: new Map() };
  const current = memo;
  const key = `${SUMMARY_SHAPE}:${JSON.stringify(filter)}`;
  let parts = current.summaries.get(key);
  if (!parts) {
    if (current.summaries.size >= MAX_SUMMARIES) current.summaries.clear();
    parts = new Map();
    current.summaries.set(key, parts);
  }
  const names = wanted(need);
  const missing = names.filter((n) => !parts.has(n));
  if (missing.length > 0) {
    for (const [name, value] of await readParts(db, key, version, missing)) parts.set(name, value);
    if (names.some((n) => !parts.has(n))) {
      // not made yet for this version of the table: work it out once, and keep all its parts
      current.rows ??= await statRows(db, ALL);
      const made = split(aggregate(current.rows, filter));
      for (const [name, value] of made) parts.set(name, value);
      await storeParts(db, key, version, made);
    }
  }
  // the rows themselves are the players of the summary (the page works out the spread of some sums over them)
  current.rows ??= await statRows(db, ALL);
  return join(
    parts,
    current.rows.filter((r) => matches(r, filter)),
  );
}
