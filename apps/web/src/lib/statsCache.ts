// A cache of the statistics summary. Every visit used to read every row of `game_stats` and work the averages out again. Now the rows are read once and kept
// in memory (the isolate that serves the page) together with the summary of each filter that was asked for; both stay valid until a row of `game_stats`
// is written. That is found with one cheap question, the highest row id of the table: every write (a game that ends, a backfill with INSERT OR REPLACE)
// gives its row a new, higher id. So the page is never older than the last write, and a visit to an unchanged table costs that one question.
// Past a few thousand rows this should read a precomputed summary instead of every row: docs/stats-scaling.md.
import type { Db } from "./db";
import { statRows } from "./queries";
import { type StatFilter, type Stats, aggregate } from "./stats";
import type { StatRow } from "./stats";

/** The most summaries kept for one version of the table (there are at most a few hundred filters; the cache is emptied whenever the table changes). */
const MAX_SUMMARIES = 200;

interface Memo {
  version: number;
  rows: StatRow[] | null;
  summaries: Map<string, Stats>;
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

const ALL: StatFilter = { players: null, expansion: null, rated: null, who: null };

/** The summary for a filter: from the cache when the table has not changed since, else made from the rows (read again only if the table changed). */
export async function cachedStats(db: Db, filter: StatFilter): Promise<Stats> {
  const version = await statsVersion(db);
  if (memo === null || memo.version !== version) memo = { version, rows: null, summaries: new Map() };
  const key = JSON.stringify(filter);
  const hit = memo.summaries.get(key);
  if (hit) return hit;
  const current = memo;
  current.rows ??= await statRows(db, ALL);
  const stats = aggregate(current.rows, filter);
  if (current.summaries.size >= MAX_SUMMARIES) current.summaries.clear();
  current.summaries.set(key, stats);
  return stats;
}
