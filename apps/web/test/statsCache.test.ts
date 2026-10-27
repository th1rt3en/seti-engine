import { beforeEach, describe, expect, it } from "vitest";
import { SqliteDb, migrationSql } from "../src/lib/db";
import { statRows } from "../src/lib/queries";
import { aggregate, parseFilter } from "../src/lib/stats";
import { cachedStats, clearStatsCache } from "../src/lib/statsCache";

/** The real tables (the migrations of the Worker) in memory, counting what it is asked and able to lose the table of the summaries. */
class CountingDb extends SqliteDb {
  rowReads = 0;
  summaryReads = 0;
  summaryWrites = 0;
  constructor() {
    super(":memory:", migrationSql());
  }
  override async all<T>(sql: string, ...params: unknown[]): Promise<T[]> {
    if (sql.includes("FROM game_stats s")) this.rowReads++;
    if (sql.includes("FROM stats_summary")) this.summaryReads++;
    return super.all<T>(sql, ...params);
  }
  override async run(sql: string, ...params: unknown[]): Promise<void> {
    if (sql.includes("INSERT OR REPLACE INTO stats_summary")) this.summaryWrites++;
    return super.run(sql, ...params);
  }
  async addRow(id: string, players = 2, score = 100): Promise<void> {
    await this.run(
      "INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES (?, 'finished', '{}', '{}', 1, 1)",
      id,
    );
    await this.run(
      `INSERT OR REPLACE INTO game_stats (game_id, seat, user_id, players, rated, expansion, rank, won, score, org, org_offered_json, species_json, counters_json, ended_at)
       VALUES (?, 0, ?, ?, 1, 1, 1, 1, ?, 'stratus_core', '[]', '["arkhos"]', ?, 1)`,
      id,
      `user-${id}`,
      players,
      score,
      JSON.stringify({ "action.launch": 2, "stats.version": 12, "alien.arkhos.games": 1, "alien.arkhos.explore.vp": 5 }),
    );
  }
}

describe("the summary of the statistics", () => {
  beforeEach(clearStatsCache);

  it("is worked out once for a table, stored in parts, and then only read", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    const first = await cachedStats(db, parseFilter({}));
    expect(first.rows).toBe(1);
    expect(db.summaryWrites).toBeGreaterThan(2); // the core, the fresh numbers, the cards, the species
    expect(await db.all("SELECT part FROM stats_summary")).not.toHaveLength(0);
    clearStatsCache(); // another isolate: it finds the summary in the table and does not work it out
    const writes = db.summaryWrites;
    const second = await cachedStats(db, parseFilter({}));
    expect(db.summaryWrites).toBe(writes);
    expect(JSON.stringify(second)).toBe(JSON.stringify(first));
  });

  it("gives the same numbers as working them out from the rows", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    await db.addRow("g2", 3, 140);
    const filter = parseFilter({ players: "2" });
    await cachedStats(db, filter);
    clearStatsCache();
    const fromTable = await cachedStats(db, filter); // read back from the table of the summaries
    const direct = aggregate(await statRows(db, parseFilter({})), filter);
    expect(JSON.parse(JSON.stringify(fromTable))).toEqual(JSON.parse(JSON.stringify(direct))); // the same numbers (the order of the fields is not one)
  });

  it("reads only the parts that the tab shows", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    await cachedStats(db, parseFilter({}));
    clearStatsCache();
    const light = await cachedStats(db, parseFilter({}), { cards: false, alien: false });
    expect(light.cards).toEqual([]); // not read: the tab does not show them
    expect(Object.keys(light.alien)).toEqual([]);
    const aliens = await cachedStats(db, parseFilter({}), { cards: false, alien: true });
    expect(aliens.alien.arkhos?.rows).toBe(1);
  });

  it("works out the summary again after a row was written (the old summaries are deleted)", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(1);
    await db.addRow("g2"); // a game ended: its row has a new, higher id
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(2);
    const versions = await db.all<{ version: number }>("SELECT DISTINCT version FROM stats_summary");
    expect(versions).toHaveLength(1);
  });

  it("keeps working without the table of the summaries (the migration is not applied yet)", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    await db.run("DROP TABLE stats_summary");
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(1);
    clearStatsCache();
    expect((await cachedStats(db, parseFilter({}))).rows).toBe(1);
  });

  it("makes another filter from the rows that it already has, and works with an empty table", async () => {
    const db = new CountingDb();
    await db.addRow("g1");
    await cachedStats(db, parseFilter({}));
    const three = await cachedStats(db, parseFilter({ players: "3" }));
    expect(three.rows).toBe(0);
    expect(db.rowReads).toBe(1);
    const empty = new CountingDb();
    expect((await cachedStats(empty, parseFilter({}))).rows).toBe(0);
  });
});
