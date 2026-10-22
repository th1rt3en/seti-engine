// What the administrator's page reads and changes in the database: the accounts (delete, set or reset the rating) and the open games.
import type { Db } from "./db";

export interface AccountRow {
  id: string;
  name: string;
  is_guest: number;
  created_at: number;
  rating: number | null;
  rated_games: number | null;
  /** a lobby or a game that is being played: such an account is not deleted before the game is cancelled */
  open_games: number;
}

const LIKE = (q: string): string => `%${q.replace(/[\\%_]/g, (c) => `\\${c}`)}%`;

export async function listAccounts(db: Db, q: string, limit: number, offset: number): Promise<AccountRow[]> {
  return db.all<AccountRow>(
    `SELECT u.id, u.name, u.is_guest, u.created_at, r.rating, r.games AS rated_games,
       (SELECT COUNT(*) FROM game_players p JOIN games g ON g.id = p.game_id WHERE p.user_id = u.id AND g.status IN ('lobby', 'playing')) AS open_games
     FROM users u LEFT JOIN ratings r ON r.user_id = u.id
     WHERE u.name LIKE ? ESCAPE '\\' ORDER BY u.is_guest, lower(u.name) LIMIT ? OFFSET ?`,
    LIKE(q),
    limit,
    offset,
  );
}

export async function countAccounts(db: Db, q: string): Promise<number> {
  const row = (await db.all<{ n: number }>("SELECT COUNT(*) AS n FROM users WHERE name LIKE ? ESCAPE '\\'", LIKE(q)))[0];
  return row?.n ?? 0;
}

/** Sets the rating of an account, whatever it was (the number of rated games is kept). */
export async function setRating(db: Db, userId: string, rating: number, now: number): Promise<void> {
  await db.run(
    `INSERT INTO ratings (user_id, rating, games, updated_at) VALUES (?, ?, 0, ?)
     ON CONFLICT(user_id) DO UPDATE SET rating = excluded.rating, updated_at = excluded.updated_at`,
    userId,
    Math.round(rating),
    now,
  );
}

/** Back to the start: the account has no rating row, so it is unrated at 0 again (the history of past games stays). */
export async function resetRating(db: Db, userId: string): Promise<void> {
  await db.run("DELETE FROM ratings WHERE user_id = ?", userId);
}

/**
 * Deletes an account: the user, the sessions and the rating. The games it played stay in the history under the name it had. Refused (false) while
 * the account sits in a lobby or in a game that is being played.
 */
export async function deleteAccount(db: Db, userId: string): Promise<boolean> {
  const open = (
    await db.all<{ n: number }>(
      "SELECT COUNT(*) AS n FROM game_players p JOIN games g ON g.id = p.game_id WHERE p.user_id = ? AND g.status IN ('lobby', 'playing')",
      userId,
    )
  )[0];
  if ((open?.n ?? 0) > 0) return false;
  await db.run("DELETE FROM sessions WHERE user_id = ?", userId);
  await db.run("DELETE FROM ratings WHERE user_id = ?", userId);
  await db.run("DELETE FROM rating_history WHERE user_id = ?", userId);
  await db.run("DELETE FROM users WHERE id = ?", userId);
  return true;
}

export interface OpenGame {
  id: string;
  status: string;
  rated: number;
  options_json: string;
  created_at: number;
  started_at: number | null;
  /** the number of the game, in the address of its page */
  num: number | null;
  seats: { name: string; num: number | null }[];
}

/** The lobbies and the games being played, the oldest first. */
export async function openGames(db: Db, limit: number, offset: number): Promise<OpenGame[]> {
  const games = await db.all<Omit<OpenGame, "seats">>(
    `SELECT g.id, gn.num, g.status, g.rated, g.options_json, g.created_at, g.started_at FROM games g LEFT JOIN game_nums gn ON gn.game_id = g.id
      WHERE g.status IN ('lobby', 'playing') ORDER BY g.created_at LIMIT ? OFFSET ?`,
    limit,
    offset,
  );
  const out: OpenGame[] = [];
  for (const g of games) {
    const seats = await db.all<{ name: string; num: number | null }>(
      "SELECT p.name AS name, un.num AS num FROM game_players p LEFT JOIN user_nums un ON un.user_id = p.user_id WHERE p.game_id = ? ORDER BY p.seat",
      g.id,
    );
    out.push({ ...g, seats });
  }
  return out;
}

export async function countOpenGames(db: Db): Promise<number> {
  const row = (await db.all<{ n: number }>("SELECT COUNT(*) AS n FROM games WHERE status IN ('lobby', 'playing')"))[0];
  return row?.n ?? 0;
}

export async function allOpenGameIds(db: Db): Promise<string[]> {
  return (await db.all<{ id: string }>("SELECT id FROM games WHERE status IN ('lobby', 'playing') ORDER BY created_at")).map((r) => r.id);
}
