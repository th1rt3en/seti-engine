// The D1 result sink: games, players, logs and ratings (checkpoint writes only: the start and the end of a game, decision D6).
import { settle } from "./ratings.js";
import type { GameRecord, LogEntry, Meta, ResultSink } from "./room.js";

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
         ON CONFLICT(id) DO UPDATE SET status = excluded.status`,
        meta.id,
        meta.status,
        JSON.stringify(meta.options),
        JSON.stringify(meta.clock),
        meta.rated ? 1 : 0,
        meta.createdAt,
      ),
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
    ]);
  }

  async removeLobby(id: string): Promise<void> {
    await this.db.batch([
      this.db.prepare("DELETE FROM game_players WHERE game_id = ?").bind(id),
      this.db.prepare("DELETE FROM games WHERE id = ? AND status IN ('lobby', 'cancelled')").bind(id),
    ]);
  }

  async recordStart(meta: Meta): Promise<void> {
    const q = (sql: string, ...v: unknown[]): Statement => this.db.prepare(sql).bind(...v);
    await this.db.batch([
      q(
        `INSERT INTO games (id, status, options_json, clock_json, rated, created_at, started_at) VALUES (?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET status = excluded.status, options_json = excluded.options_json, started_at = excluded.started_at`,
        meta.id,
        meta.status,
        JSON.stringify(meta.options),
        JSON.stringify(meta.clock),
        meta.rated ? 1 : 0,
        meta.createdAt,
        meta.startedAt ?? null,
      ),
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

  async recordEnd(rec: GameRecord, log: LogEntry[]): Promise<void> {
    const q = (sql: string, ...v: unknown[]): Statement => this.db.prepare(sql).bind(...v);
    const ids = rec.meta.seats.flatMap((s) => (s === null ? [] : [s.id]));
    const current = new Map<string, number>();
    if (rec.rated && ids.length > 0) {
      const marks = ids.map(() => "?").join(", ");
      const rows = await this.db
        .prepare(`SELECT user_id, rating FROM ratings WHERE user_id IN (${marks})`)
        .bind(...ids)
        .all<{ user_id: string; rating: number }>();
      for (const r of rows.results) current.set(r.user_id, r.rating);
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
