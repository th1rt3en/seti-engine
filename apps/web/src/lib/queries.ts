// Reads for the lobby, the leaderboard and the profiles.
import type { Db } from "./db";

export interface LobbyGame {
  id: string;
  rated: boolean;
  players: number;
  seats: string[];
  clock: string;
  host: string;
}

export interface LeaderRow {
  user_id: string;
  name: string;
  rating: number;
  games: number;
}

export interface HistoryRow {
  game_id: string;
  rating_before: number;
  rating_after: number;
  rank: number;
  at: number;
}

export interface RecentGame {
  id: string;
  status: string;
  rated_counted: number;
  reason: string | null;
  ended_at: number | null;
  rank: number | null;
  score: number | null;
  options_json: string;
}

export async function lobbyGames(db: Db, limit = 50): Promise<LobbyGame[]> {
  const games = await db.all<{ id: string; rated: number; options_json: string; clock_json: string }>(
    "SELECT id, rated, options_json, clock_json FROM games WHERE status = 'lobby' ORDER BY created_at DESC LIMIT ?",
    limit,
  );
  const out: LobbyGame[] = [];
  for (const g of games) {
    const seats = await db.all<{ name: string }>("SELECT name FROM game_players WHERE game_id = ? ORDER BY seat", g.id);
    const options = JSON.parse(g.options_json) as { players: number };
    out.push({
      id: g.id,
      rated: g.rated === 1,
      players: options.players,
      seats: seats.map((s) => s.name),
      clock: describeClock(g.clock_json),
      host: seats[0]?.name ?? "?",
    });
  }
  return out.filter((g) => g.seats.length < g.players);
}

/** A length of time in words for the lobby: "5 min", "1 min 30 s", "3 days", "9 h". */
export function spanText(ms: number): string {
  const s = Math.round(ms / 1000);
  const parts: string[] = [];
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) parts.push(`${d} day${d === 1 ? "" : "s"}`);
  if (h > 0) parts.push(`${h} h`);
  if (m > 0) parts.push(`${m} min`);
  if (sec > 0) parts.push(`${sec} s`);
  return parts.join(" ") || "0 s";
}

export function describeClock(json: string): string {
  const c = JSON.parse(json) as { kind: string; ms?: number; initialMs?: number; incrementMs?: number };
  if (c.kind === "per_turn") return `${Math.round((c.ms ?? 0) / 3_600_000)} h per turn`;
  if (c.kind === "bank") return `${spanText(c.initialMs ?? 0)} + ${spanText(c.incrementMs ?? 0)} per turn`;
  return "no clock";
}

export function leaderboard(db: Db, limit = 100): Promise<LeaderRow[]> {
  return db.all<LeaderRow>(
    `SELECT r.user_id, u.name, r.rating, r.games FROM ratings r JOIN users u ON u.id = r.user_id
     WHERE u.is_guest = 0 ORDER BY r.rating DESC, r.games DESC LIMIT ?`,
    limit,
  );
}

export async function profile(db: Db, userId: string) {
  const user = (
    await db.all<{ id: string; name: string; is_guest: number; created_at: number }>(
      "SELECT id, name, is_guest, created_at FROM users WHERE id = ?",
      userId,
    )
  )[0];
  if (user === undefined) return null;
  const rating = (await db.all<{ rating: number; games: number }>("SELECT rating, games FROM ratings WHERE user_id = ?", userId))[0];
  const history = await db.all<HistoryRow>(
    "SELECT game_id, rating_before, rating_after, rank, at FROM rating_history WHERE user_id = ? ORDER BY at DESC LIMIT 50",
    userId,
  );
  const recent = await db.all<RecentGame>(
    `SELECT g.id, g.status, g.rated_counted, g.reason, g.ended_at, p.rank, p.score, g.options_json
     FROM game_players p JOIN games g ON g.id = p.game_id WHERE p.user_id = ? AND g.status IN ('finished', 'playing')
     ORDER BY g.created_at DESC LIMIT 30`,
    userId,
  );
  return { user, rating: rating ?? null, history, recent };
}
