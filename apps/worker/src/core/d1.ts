import type { GameStats } from "./engine.js";
// The D1 result sink: games, players, logs and ratings (checkpoint writes only: the start and the end of a game, decision D6).
import { settle } from "./ratings.js";
import type { GameRecord, LogEntry, Meta, Result, ResultSink } from "./room.js";

/** The part of the D1 API that is used (so a test can run it against SQLite). */
export interface Db {
  prepare(sql: string): Statement;
  batch(statements: Statement[]): Promise<unknown[]>;
}

export interface Statement {
  bind(...values: unknown[]): Statement;
  all<T = Record<string, unknown>>(): Promise<{ results: T[] }>;
}

export class D1Sink implements ResultSink {
  constructor(private readonly db: Db) {}

  async recordLobby(meta: Meta): Promise<void> {
    const q = (sql: string, ...v: unknown[]): Statement => this.db.prepare(sql).bind(...v);
    await this.db.batch([
      q(
        `INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET status = excluded.status, rated = excluded.rated`,
        meta.id,
        meta.status,
        JSON.stringify(meta.options),
        JSON.stringify(meta.clock),
        meta.rated ? 1 : 0,
        meta.createdAt,
      ),
      // the number of the game, in the address of its page: an autoincrement key, so a number is never given twice (a destroyed lobby keeps its own)
      q("INSERT INTO game_nums (game_id) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM game_nums WHERE game_id = ?)", meta.id, meta.id),
      q("DELETE FROM game_players WHERE game_id = ?", meta.id),
      ...meta.seats.flatMap((s, seat) =>
        s === null
          ? []
          : [
              q(
                "INSERT INTO game_players (game_id, seat, user_id, name, registered) VALUES (?, ?, ?, ?, ?)",
                meta.id,
                seat,
                s.id,
                s.name,
                s.registered ? 1 : 0,
              ),
            ],
      ),
      q("DELETE FROM lobby_invites WHERE game_id = ?", meta.id),
      ...(meta.invites ?? []).map((i) =>
        q(
          "INSERT INTO lobby_invites (game_id, seat, user_id, name, host_name, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
          meta.id,
          i.seat,
          i.id,
          i.name,
          meta.seats.find((s) => s?.id === meta.host)?.name ?? "",
          i.status,
          i.at,
        ),
      ),
    ]);
  }

  async gameNum(id: string): Promise<number | null> {
    const rows = await this.db.prepare("SELECT num FROM game_nums WHERE game_id = ?").bind(id).all<{ num: number }>();
    return rows.results[0]?.num ?? null;
  }

  async removeLobby(id: string): Promise<void> {
    await this.db.batch([
      this.db.prepare("DELETE FROM game_players WHERE game_id = ?").bind(id),
      this.db.prepare("DELETE FROM lobby_invites WHERE game_id = ?").bind(id),
      this.db.prepare("DELETE FROM games WHERE id = ? AND status IN ('lobby', 'cancelled')").bind(id),
    ]);
  }

  async recordCancelled(meta: Meta): Promise<void> {
    // no result and no rating: the game is only marked as cancelled (rated_counted stays 0)
    await this.db
      .prepare("UPDATE games SET status = 'cancelled', reason = 'cancelled', ended_at = ? WHERE id = ? AND status IN ('lobby', 'playing')")
      .bind(meta.endedAt ?? 0, meta.id)
      .all();
  }

  async recordStart(meta: Meta): Promise<void> {
    const q = (sql: string, ...v: unknown[]): Statement => this.db.prepare(sql).bind(...v);
    await this.db.batch([
      q(
        `INSERT INTO games (id, status, options_json, clock_json, rated, created_at, started_at) VALUES (?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET status = excluded.status, options_json = excluded.options_json, started_at = excluded.started_at, rated = excluded.rated`,
        meta.id,
        meta.status,
        JSON.stringify(meta.options),
        JSON.stringify(meta.clock),
        meta.rated ? 1 : 0,
        meta.createdAt,
        meta.startedAt ?? null,
      ),
      q("INSERT INTO game_nums (game_id) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM game_nums WHERE game_id = ?)", meta.id, meta.id),
      q("DELETE FROM lobby_invites WHERE game_id = ?", meta.id), // the game has started: no invitation is left to answer
      ...meta.seats.flatMap((s, seat) =>
        s === null
          ? []
          : [
              q(
                "INSERT OR REPLACE INTO game_players (game_id, seat, user_id, name, registered) VALUES (?, ?, ?, ?, ?)",
                meta.id,
                seat,
                s.id,
                s.name,
                s.registered ? 1 : 0,
              ),
            ],
      ),
    ]);
  }

  /** The statistics of a game that was played to its end: a row for each player (migrations/0006_game_stats.sql). */
  async recordStats(meta: Meta, result: Result, stats: GameStats): Promise<void> {
    const rows = stats.players.flatMap((p) => {
      const who = meta.seats[p.seat];
      const ranked = result.ranking.find((r) => r.seat === p.seat);
      if (!who || !ranked) return [];
      return [
        this.db
          .prepare(
            `INSERT OR REPLACE INTO game_stats (game_id, seat, user_id, players, rated, expansion, rank, won, score, org, org_offered_json, species_json, counters_json, ended_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          )
          .bind(
            meta.id,
            p.seat,
            who.id,
            meta.seats.length,
            meta.rated ? 1 : 0,
            stats.expansion ? 1 : 0,
            ranked.rank,
            result.winners.includes(p.seat) ? 1 : 0,
            ranked.score,
            p.org,
            JSON.stringify(p.org_offered),
            JSON.stringify(stats.species),
            JSON.stringify(p.counters),
            meta.endedAt ?? 0,
          ),
      ];
    });
    if (rows.length > 0) await this.db.batch(rows);
  }

  async recordEnd(rec: GameRecord, log: LogEntry[]): Promise<void> {
    const q = (sql: string, ...v: unknown[]): Statement => this.db.prepare(sql).bind(...v);
    const ids = rec.meta.seats.flatMap((s) => (s === null ? [] : [s.id]));
    const current = new Map<string, { rating: number; games: number }>();
    // a game with an AI is never rated: no rating is read or written, whatever the record says
    if (rec.rated && ids.length > 0 && !ids.some((id) => id.startsWith("bot:"))) {
      const marks = ids.map(() => "?").join(", ");
      const rows = await this.db
        .prepare(`SELECT user_id, rating, games FROM ratings WHERE user_id IN (${marks})`)
        .bind(...ids)
        .all<{ user_id: string; rating: number; games: number }>();
      for (const r of rows.results) current.set(r.user_id, { rating: r.rating, games: r.games });
    }
    const updates = settle(rec, current);
    const at = rec.meta.endedAt ?? 0;
    const statements: Statement[] = [
      q(
        "UPDATE games SET status = ?, reason = ?, result_json = ?, actions = ?, rated_counted = ?, ended_at = ? WHERE id = ?",
        rec.meta.status,
        rec.result.reason,
        JSON.stringify(rec.result),
        rec.actions,
        updates.length > 0 ? 1 : 0,
        at,
        rec.meta.id,
      ),
      q("INSERT OR REPLACE INTO game_logs (game_id, log_json) VALUES (?, ?)", rec.meta.id, JSON.stringify(log)),
      ...rec.result.ranking.map((r) =>
        q("UPDATE game_players SET rank = ?, score = ? WHERE game_id = ? AND seat = ?", r.rank, r.score, rec.meta.id, r.seat),
      ),
    ];
    for (const u of updates) {
      statements.push(
        q(
          `INSERT INTO ratings (user_id, rating, games, updated_at) VALUES (?, ?, 1, ?)
           ON CONFLICT(user_id) DO UPDATE SET rating = excluded.rating, games = games + 1, updated_at = excluded.updated_at`,
          u.userId,
          u.after,
          at,
        ),
        q(
          "INSERT INTO rating_history (game_id, user_id, rating_before, rating_after, rank, at) VALUES (?, ?, ?, ?, ?, ?)",
          rec.meta.id,
          u.userId,
          u.before,
          u.after,
          u.rank,
          at,
        ),
        q(
          "UPDATE game_players SET rating_before = ?, rating_after = ? WHERE game_id = ? AND seat = ?",
          u.before,
          u.after,
          rec.meta.id,
          u.seat,
        ),
      );
    }
    await this.db.batch(statements);
  }
}
