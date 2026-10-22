// The D1 sink runs here against SQLite (node:sqlite) with the real migration.
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { D1Sink, type Db, type Statement } from "../src/core/d1.js";
import type { GameRecord, Meta, Result } from "../src/core/room.js";
import { alice, bob, cy, guest } from "./helpers.js";

// vite does not know node:sqlite, so it is loaded by require
const { DatabaseSync } = createRequire(import.meta.url)("node:sqlite") as typeof import("node:sqlite");

class SqliteDb implements Db {
  readonly sql = new DatabaseSync(":memory:");
  constructor() {
    this.sql.exec(readFileSync(new URL("../migrations/0001_init.sql", import.meta.url), "utf8"));
    this.sql.exec(readFileSync(new URL("../migrations/0006_game_stats.sql", import.meta.url), "utf8"));
    this.sql.exec(readFileSync(new URL("../migrations/0008_numeric_ids.sql", import.meta.url), "utf8"));
  }
  prepare(query: string): Statement {
    const run = (values: unknown[]): Statement => {
      const st: Statement = {
        bind: (...v: unknown[]) => run(v),
        all: async <T>() => ({ results: this.sql.prepare(query).all(...(values as never[])) as T[] }),
        // biome-ignore lint/suspicious/noExplicitAny: the batch below runs the statement
        ...({ _exec: () => this.sql.prepare(query).run(...(values as never[])) } as any),
      };
      return st;
    };
    return run([]);
  }
  async batch(statements: Statement[]): Promise<unknown[]> {
    this.sql.exec("BEGIN");
    try {
      const out = statements.map((s) => (s as unknown as { _exec: () => unknown })._exec());
      this.sql.exec("COMMIT");
      return out;
    } catch (e) {
      this.sql.exec("ROLLBACK");
      throw e;
    }
  }
}

function record(id: string, seats: (typeof alice)[], ranks: number[], rated: boolean, reason: Result["reason"] = "completed"): GameRecord {
  const meta: Meta = {
    id,
    status: "finished",
    options: { players: seats.length, seed: 7 } as Options,
    clock: { kind: "none" },
    rated,
    seats,
    host: "u-alice",
    joined: ["u-alice", "u-bob"],
    createdAt: 1,
    startedAt: 2,
    endedAt: 3,
  };
  const result: Result = {
    reason,
    ranking: seats.map((_, seat) => ({ seat, rank: ranks[seat] ?? 1, score: 100 - 10 * (ranks[seat] ?? 1) })),
    winners: [ranks.indexOf(1)],
    finalScores: [],
  };
  return { meta, result, actions: 40, rated };
}

describe("D1 sink", () => {
  it("gives a game its number once, in the order the games were made, and never gives it again", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const lobby = (id: string): Meta => ({ ...record(id, [alice, bob], [1, 2], false).meta, status: "lobby" });
    await sink.recordLobby(lobby("first"));
    await sink.recordLobby(lobby("second"));
    await sink.recordLobby(lobby("first")); // a seat changed: the same game, the same number
    await sink.recordStart({ ...lobby("first"), status: "playing" });
    await sink.removeLobby("second"); // destroyed
    await sink.recordLobby(lobby("third"));
    const nums = db.sql.prepare("SELECT game_id, num FROM game_nums ORDER BY num").all();
    expect(nums).toEqual([
      { game_id: "first", num: 1 },
      { game_id: "second", num: 2 },
      { game_id: "third", num: 3 },
    ]);
  });

  it("writes the game, its players and its log", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const rec = record("g1", [alice, bob], [1, 2], false);
    await sink.recordStart({ ...rec.meta, status: "playing" });
    await sink.recordEnd(rec, [{ seq: 0, seat: 0, action: { type: "score" }, at: 5, events: [] }]);
    const g = db.sql.prepare("SELECT status, reason, rated, rated_counted, actions FROM games WHERE id = 'g1'").get() as Record<
      string,
      unknown
    >;
    expect(g).toMatchObject({ status: "finished", reason: "completed", rated: 0, rated_counted: 0, actions: 40 });
    const players = db.sql.prepare("SELECT seat, user_id, rank, score FROM game_players WHERE game_id = 'g1' ORDER BY seat").all();
    expect(players).toEqual([
      expect.objectContaining({ seat: 0, user_id: "u-alice", rank: 1, score: 90 }),
      expect.objectContaining({ seat: 1, user_id: "u-bob", rank: 2, score: 80 }),
    ]);
    const log = db.sql.prepare("SELECT log_json FROM game_logs WHERE game_id = 'g1'").get() as { log_json: string };
    expect(JSON.parse(log.log_json)).toHaveLength(1);
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM ratings").get()).toEqual({ n: 0 });
  });

  it("the statistics of a game are written for each player", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const rec = record("g1", [alice, bob], [1, 2], false);
    await sink.recordStart({ ...rec.meta, status: "playing" });
    await sink.recordEnd(rec, []);
    const stats = {
      version: 1,
      expansion: true,
      species: ["anomalies", "centaurians"],
      rounds: 5,
      players: [
        { seat: 0, org: "stratus_core", org_offered: ["stratus_core", "turing_systems"], counters: { "action.launch": 3 } },
        { seat: 1, org: null, org_offered: [], counters: { "action.launch": 1 } },
      ],
    };
    await sink.recordStats(rec.meta, rec.result, stats);
    await sink.recordStats(rec.meta, rec.result, stats); // the same game again replaces its rows
    const rows = db.sql
      .prepare("SELECT seat, user_id, players, expansion, rank, won, score, org, counters_json FROM game_stats ORDER BY seat")
      .all();
    expect(rows).toEqual([
      expect.objectContaining({ seat: 0, user_id: "u-alice", players: 2, expansion: 1, rank: 1, won: 1, score: 90, org: "stratus_core" }),
      expect.objectContaining({ seat: 1, user_id: "u-bob", rank: 2, won: 0, org: null }),
    ]);
    expect(JSON.parse((rows[0] as { counters_json: string }).counters_json)).toEqual({ "action.launch": 3 });
  });

  it("a rated game updates the ratings and the history, and the next game builds on them", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const one = record("g1", [alice, bob], [1, 2], true);
    await sink.recordStart({ ...one.meta, status: "playing" });
    await sink.recordEnd(one, []);
    const ratings = () =>
      Object.fromEntries(
        (db.sql.prepare("SELECT user_id, rating, games FROM ratings").all() as { user_id: string; rating: number; games: number }[]).map(
          (r) => [r.user_id, [r.rating, r.games]],
        ),
      );
    expect(ratings()).toEqual({ "u-alice": [30, 1], "u-bob": [0, 1] }); // new players: K = 60; below 100 nothing is lost
    const two = record("g2", [alice, bob], [2, 1], true);
    await sink.recordStart({ ...two.meta, status: "playing" });
    await sink.recordEnd(two, []);
    const r = ratings();
    expect(r["u-alice"]?.[1]).toBe(2);
    expect(r["u-bob"]?.[0]).toBeGreaterThan(0);
    expect(r["u-alice"]?.[0]).toBe(30); // alice lost, but she is below 100
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM rating_history").get()).toEqual({ n: 4 });
    expect(db.sql.prepare("SELECT rated_counted FROM games WHERE id = 'g2'").get()).toEqual({ rated_counted: 1 });
    const gp = db.sql.prepare("SELECT rating_before, rating_after FROM game_players WHERE game_id = 'g1' AND seat = 0").get();
    expect(gp).toEqual({ rating_before: 0, rating_after: 30 });
  });

  it("three players move by at most K and an unrated game leaves the ratings alone", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const g = record("g1", [alice, bob, cy], [1, 2, 3], true);
    await sink.recordStart({ ...g.meta, status: "playing" });
    await sink.recordEnd(g, []);
    const rows = db.sql.prepare("SELECT rating FROM ratings ORDER BY rating").all() as { rating: number }[];
    expect(rows.map((r) => r.rating)).toEqual([0, 0, 30]);
    const solo = record("g2", [guest], [1], false);
    await sink.recordStart({ ...solo.meta, status: "playing" });
    await sink.recordEnd(solo, []);
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM ratings").get()).toEqual({ n: 3 });
  });

  it("a lobby game is listed with its seats, and they follow the joins", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const g = record("g1", [alice, null as never], [1, 2], false);
    await sink.recordLobby({ ...g.meta, status: "lobby", seats: [alice, null] });
    expect(db.sql.prepare("SELECT status FROM games WHERE id = 'g1'").get()).toEqual({ status: "lobby" });
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM game_players WHERE game_id = 'g1'").get()).toEqual({ n: 1 });
    await sink.recordLobby({ ...g.meta, status: "lobby", seats: [alice, bob] });
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM game_players WHERE game_id = 'g1'").get()).toEqual({ n: 2 });
  });

  it("the migration creates every table of the plan", () => {
    const db = new SqliteDb();
    const names = (db.sql.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as { name: string }[]).map((r) => r.name);
    for (const t of ["users", "sessions", "games", "game_players", "game_logs", "ratings", "rating_history"]) expect(names).toContain(t);
  });

  it("a destroyed lobby is removed with its seats, and a started game is kept", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const lobby = record("gone", [alice, bob], [1, 2], false);
    await sink.recordLobby({ ...lobby.meta, status: "lobby", seats: [alice, null] });
    await sink.removeLobby("gone");
    expect(db.sql.prepare("SELECT id FROM games WHERE id = 'gone'").all()).toEqual([]);
    expect(db.sql.prepare("SELECT seat FROM game_players WHERE game_id = 'gone'").all()).toEqual([]);
    const kept = record("kept", [alice, bob], [1, 2], false);
    await sink.recordStart({ ...kept.meta, status: "playing" });
    await sink.removeLobby("kept");
    expect(db.sql.prepare("SELECT id FROM games WHERE id = 'kept'").all()).toHaveLength(1);
  });

  it("a game cancelled by an administrator is marked cancelled, with no rating and no history", async () => {
    const db = new SqliteDb();
    const sink = new D1Sink(db);
    const rec = record("quit", [alice, bob], [1, 2], true);
    await sink.recordStart({ ...rec.meta, status: "playing" });
    await sink.recordCancelled({ ...rec.meta, status: "cancelled", endedAt: 77 });
    expect(db.sql.prepare("SELECT status, reason, ended_at, rated_counted FROM games WHERE id = 'quit'").get()).toEqual({
      status: "cancelled",
      reason: "cancelled",
      ended_at: 77,
      rated_counted: 0,
    });
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM ratings").get()).toEqual({ n: 0 });
    expect(db.sql.prepare("SELECT COUNT(*) AS n FROM rating_history").get()).toEqual({ n: 0 });
  });
});
