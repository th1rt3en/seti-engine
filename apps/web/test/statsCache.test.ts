import { beforeEach, describe, expect, it } from "vitest";
import type { Db } from "../src/lib/db";
import { parseFilter } from "../src/lib/stats";
import { cachedStats, clearStatsCache } from "../src/lib/statsCache";

/** A database with a table of statistics that counts what it is asked. */
class CountingDb implements Db {
  version = 1;
  rows: { game_id: string; user_id: string; players: number }[] = [{ game_id: "g1", user_id: "u1", players: 2 }];
  versionQueries = 0;
  rowQueries = 0;
  async all<T>(sql: string): Promise<T[]> {
    if (sql.includes("MAX(rowid)")) {
      this.versionQueries++;
      return [{ v: this.version }] as T[];
    }
    this.rowQueries++;
    return this.rows.map((r) => ({
      ...r,
      seat: 0,
      rated: 1,
      expansion: 0,
      rank: 1,
      won: 1,
      score: 100,
      org: null,
      org_offered_json: "[]",
      species_json: "[]",
      counters_json: JSON.stringify({ "action.launch": 2 }),
      elo: null,
    })) as T[];
  }
  async run(): Promise<void> {}
}

describe("the cache of the statistics summary", () => {
  beforeEach(clearStatsCache);

  it("reads the rows once and asks only the version while the table has not changed", async () => {
    const db = new CountingDb();
    const first = await cachedStats(db, parseFilter({}));
    const second = await cachedStats(db, parseFilter({}));
    expect(second).toBe(first); // the same summary, not worked out again
    expect(db.rowQueries).toBe(1);
    expect(db.versionQueries).toBe(2);
  });

  it("makes another filter from the rows that it already has", async () => {
    const db = new CountingDb();
    await cachedStats(db, parseFilter({}));
    const two = await cachedStats(db, parseFilter({ players: "2" }));
    const three = await cachedStats(db, parseFilter({ players: "3" }));
    expect(two.rows).toBe(1);
    expect(three.rows).toBe(0);
    expect(db.rowQueries).toBe(1);
  });

  it("reads again after a row was written", async () => {
    const db = new CountingDb();
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(1);
    db.rows.push({ game_id: "g2", user_id: "u2", players: 2 });
    db.version = 2; // a game ended: its row has a new, higher id
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(2);
    expect(db.rowQueries).toBe(2);
  });

  it("works with an empty table", async () => {
    const db = new CountingDb();
    db.rows = [];
    db.version = 0;
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(0);
  });
});
