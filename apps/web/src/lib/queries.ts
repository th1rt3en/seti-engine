// Reads for the lobby, the leaderboard and the profiles.
import type { Db } from "./db";

export interface LobbyGame {
  id: string;
  rated: boolean;
  players: number;
  seats: string[];
  clock: string;
  host: string;
  /** the options that change how the game feels, for the badges on the lobby cards */
  promo: boolean;
  expansion: boolean;
  organizations: boolean;
  solo: boolean;
  /** "realtime" (minutes), "turnbased" (a day or more) or "none" (no clock), for the filter of the lobby */
  mode: "realtime" | "turnbased" | "none";
}

export interface PlayingGame {
  id: string;
  rated: boolean;
  players: number;
  seats: string[];
  clock: string;
  started_at: number | null;
  actions: number;
  expansion: boolean;
  organizations: boolean;
  solo: boolean;
}

/** The games of the page of watching are the real ones: a sandbox game is practice and is not listed. */
const NOT_SANDBOX = `options_json NOT LIKE '%"sandbox":true%'`;

/** The games that are being played now, newest first, for the page where anybody can watch (`offset` and `limit` make the page). */
export async function playingGames(db: Db, limit = 100, offset = 0): Promise<PlayingGame[]> {
  const games = await db.all<{
    id: string;
    rated: number;
    options_json: string;
    clock_json: string;
    started_at: number | null;
    actions: number;
  }>(
    `SELECT id, rated, options_json, clock_json, started_at, actions FROM games WHERE status = 'playing' AND ${NOT_SANDBOX}
     ORDER BY started_at DESC LIMIT ? OFFSET ?`,
    limit,
    offset,
  );
  const out: PlayingGame[] = [];
  for (const g of games) {
    const options = JSON.parse(g.options_json) as { players: number; expansion?: boolean; organizations?: boolean };
    const seats = await db.all<{ name: string }>("SELECT name FROM game_players WHERE game_id = ? ORDER BY seat", g.id);
    out.push({
      id: g.id,
      rated: g.rated === 1,
      players: options.players,
      seats: seats.map((s) => s.name),
      clock: describeClock(g.clock_json),
      started_at: g.started_at,
      actions: g.actions,
      expansion: options.expansion === true,
      organizations: options.organizations === true,
      solo: options.players === 1,
    });
  }
  return out;
}

export async function countPlayingGames(db: Db): Promise<number> {
  const row = (await db.all<{ n: number }>(`SELECT COUNT(*) AS n FROM games WHERE status = 'playing' AND ${NOT_SANDBOX}`))[0];
  return row?.n ?? 0;
}

export interface EndedGame {
  id: string;
  rated: boolean;
  players: number;
  seats: { name: string; rank: number | null; score: number | null }[];
  /** completed, resigned, timeout or kicked */
  reason: string;
  /** the player who resigned or ran out of time */
  forfeit: string | null;
  ended_at: number | null;
  expansion: boolean;
  organizations: boolean;
  solo: boolean;
}

/** The games that are over (resigned and timed-out ones too), the latest first. */
export async function endedGames(db: Db, limit = 10, offset = 0): Promise<EndedGame[]> {
  const games = await db.all<{
    id: string;
    rated: number;
    options_json: string;
    reason: string | null;
    result_json: string | null;
    ended_at: number | null;
  }>(
    `SELECT id, rated, options_json, reason, result_json, ended_at FROM games WHERE status = 'finished' AND ${NOT_SANDBOX}
     ORDER BY ended_at DESC LIMIT ? OFFSET ?`,
    limit,
    offset,
  );
  const out: EndedGame[] = [];
  for (const g of games) {
    const options = JSON.parse(g.options_json) as { players: number; expansion?: boolean; organizations?: boolean };
    const seats = await db.all<{ name: string; rank: number | null; score: number | null; seat: number }>(
      "SELECT name, rank, score, seat FROM game_players WHERE game_id = ? ORDER BY seat",
      g.id,
    );
    let forfeitSeat: number | null = null;
    try {
      const result = g.result_json ? (JSON.parse(g.result_json) as { forfeit?: number }) : null;
      forfeitSeat = typeof result?.forfeit === "number" ? result.forfeit : null;
    } catch {
      forfeitSeat = null;
    }
    out.push({
      id: g.id,
      rated: g.rated === 1,
      players: options.players,
      seats: seats.map((x) => ({ name: x.name, rank: x.rank, score: x.score })),
      reason: g.reason ?? "completed",
      forfeit: forfeitSeat === null ? null : (seats.find((x) => x.seat === forfeitSeat)?.name ?? null),
      ended_at: g.ended_at,
      expansion: options.expansion === true,
      organizations: options.organizations === true,
      solo: options.players === 1,
    });
  }
  return out;
}

export async function countEndedGames(db: Db): Promise<number> {
  const row = (await db.all<{ n: number }>(`SELECT COUNT(*) AS n FROM games WHERE status = 'finished' AND ${NOT_SANDBOX}`))[0];
  return row?.n ?? 0;
}

export interface LeaderRow {
  user_id: string;
  name: string;
  rating: number;
  games: number;
}

export interface PlayerRow {
  user_id: string;
  name: string;
  /** 0 until the first rated game */
  rating: number;
  /** rated games that counted */
  rated_games: number;
  /** every game the player sat in that has started */
  games: number;
  joined: number;
}

/** All registered players (guests are left out), by name; `q` keeps the names that contain it. */
export async function allPlayers(db: Db, q = "", limit = 500): Promise<PlayerRow[]> {
  const like = `%${q.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
  return db.all<PlayerRow>(
    `SELECT u.id AS user_id, u.name, COALESCE(r.rating, 0) AS rating, COALESCE(r.games, 0) AS rated_games,
       (SELECT COUNT(*) FROM game_players gp JOIN games g ON g.id = gp.game_id
         WHERE gp.user_id = u.id AND g.status IN ('playing', 'finished')) AS games,
       u.created_at AS joined
     FROM users u LEFT JOIN ratings r ON r.user_id = u.id
     WHERE u.is_guest = 0 AND u.name LIKE ? ESCAPE '\\' ORDER BY u.name COLLATE NOCASE LIMIT ?`,
    like,
    limit,
  );
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
    const options = JSON.parse(g.options_json) as { players: number; promo_cards?: boolean; expansion?: boolean; organizations?: boolean };
    out.push({
      id: g.id,
      rated: g.rated === 1,
      players: options.players,
      seats: seats.map((s) => s.name),
      clock: describeClock(g.clock_json),
      host: seats[0]?.name ?? "?",
      promo: options.promo_cards === true,
      expansion: options.expansion === true,
      organizations: options.organizations === true,
      solo: options.players === 1,
      mode: clockMode(g.clock_json),
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

/** Real time (minutes), turn-based (a day or more for the start time) or no clock. */
export function clockMode(json: string): "realtime" | "turnbased" | "none" {
  const c = JSON.parse(json) as { kind: string; ms?: number; initialMs?: number };
  if (c.kind === "per_turn") return (c.ms ?? 0) >= 86_400_000 ? "turnbased" : "realtime";
  if (c.kind === "bank") return (c.initialMs ?? 0) >= 86_400_000 ? "turnbased" : "realtime";
  return "none";
}

export interface LobbyFilter {
  players?: string;
  rated?: string;
  expansion?: string;
  mode?: string;
}

/** The open games that match the lobby's filter ("" or "any" is no filter on that point). */
export function filterLobby(games: LobbyGame[], f: LobbyFilter): LobbyGame[] {
  const on = (v: string | undefined): v is string => v !== undefined && v !== "" && v !== "any";
  return games.filter(
    (g) =>
      (!on(f.players) || String(g.players) === f.players) &&
      (!on(f.rated) || (f.rated === "rated") === g.rated) &&
      (!on(f.expansion) || (f.expansion === "yes") === g.expansion) &&
      (!on(f.mode) || g.mode === f.mode),
  );
}

export function describeClock(json: string): string {
  const c = JSON.parse(json) as { kind: string; ms?: number; initialMs?: number; incrementMs?: number };
  if (c.kind === "per_turn") return `${Math.round((c.ms ?? 0) / 3_600_000)} h per turn`;
  if (c.kind === "bank") return `${spanText(c.initialMs ?? 0)} + ${spanText(c.incrementMs ?? 0)} per turn`;
  return "no clock";
}

/** The rated players, best first. `name` keeps the names that contain it (any case); `minGames` keeps those with that many rated games or more. */
export function leaderboard(db: Db, limit = 100, name = "", minGames = 0): Promise<LeaderRow[]> {
  const like = `%${name.trim().replace(/[\\%_]/g, (c) => `\\${c}`)}%`;
  return db.all<LeaderRow>(
    `SELECT r.user_id, u.name, r.rating, r.games FROM ratings r JOIN users u ON u.id = r.user_id
     WHERE u.is_guest = 0 AND u.name LIKE ? ESCAPE '\\' AND r.games >= ? ORDER BY r.rating DESC, r.games DESC LIMIT ?`,
    like,
    Math.max(0, Math.floor(minGames)),
    limit,
  );
}

export interface FinishedGame {
  rank: number | null;
  score: number | null;
  rated_counted: number;
  options_json: string;
}

export interface BucketStats {
  games: number;
  wins: number;
}

export interface ProfileStats {
  games: number;
  wins: number;
  /** wins / games as a percentage, null with no game */
  winRate: number | null;
  ratedGames: number;
  ratedWins: number;
  avgScore: number | null;
  bestScore: number | null;
  /** by the number of players: "solo", "2", "3", "4" */
  byPlayers: Record<string, BucketStats>;
  expansionGames: number;
}

/** The numbers of the profile page from a player's finished games. Sandbox games are practice and do not count. */
export function computeStats(rows: FinishedGame[]): ProfileStats {
  const byPlayers: Record<string, BucketStats> = {};
  let games = 0;
  let wins = 0;
  let ratedGames = 0;
  let ratedWins = 0;
  let expansionGames = 0;
  const scores: number[] = [];
  for (const r of rows) {
    const o = JSON.parse(r.options_json) as { players: number; sandbox?: boolean; expansion?: boolean };
    if (o.sandbox === true) continue;
    const won = r.rank === 1;
    games += 1;
    if (won) wins += 1;
    if (r.rated_counted === 1) {
      ratedGames += 1;
      if (won) ratedWins += 1;
    }
    if (o.expansion === true) expansionGames += 1;
    if (r.score !== null) scores.push(r.score);
    const key = o.players === 1 ? "solo" : String(o.players);
    const bucket = byPlayers[key] ?? { games: 0, wins: 0 };
    bucket.games += 1;
    if (won) bucket.wins += 1;
    byPlayers[key] = bucket;
  }
  return {
    games,
    wins,
    winRate: games === 0 ? null : Math.round((wins / games) * 100),
    ratedGames,
    ratedWins,
    avgScore: scores.length === 0 ? null : Math.round(scores.reduce((a, b) => a + b, 0) / scores.length),
    bestScore: scores.length === 0 ? null : Math.max(...scores),
    byPlayers,
    expansionGames,
  };
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
  const finished = await db.all<FinishedGame>(
    `SELECT p.rank, p.score, g.rated_counted, g.options_json
     FROM game_players p JOIN games g ON g.id = p.game_id WHERE p.user_id = ? AND g.status = 'finished' AND g.reason = 'completed'
     ORDER BY g.created_at DESC LIMIT 1000`,
    userId,
  );
  const ratings = history.map((h) => h.rating_after);
  const peak = Math.max(rating?.rating ?? 0, ...ratings);
  return { user, rating: rating ?? null, history, recent, stats: computeStats(finished), peak };
}

/** The time that must pass between two games that the same player creates (a second press of the button must not make a second game). */
export const CREATE_GAP_MS = 15_000;

/** Did this player create a game (sit in seat 0 of a new game) in the last moments? */
export async function createdRecently(db: Db, userId: string, now: number): Promise<boolean> {
  const rows = await db.all<{ n: number }>(
    "SELECT COUNT(*) AS n FROM games g JOIN game_players p ON p.game_id = g.id WHERE p.user_id = ? AND p.seat = 0 AND g.created_at > ?",
    userId,
    now - CREATE_GAP_MS,
  );
  return (rows[0]?.n ?? 0) > 0;
}
