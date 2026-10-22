// The integer numbers of players and games: the addresses of their pages are /players/12 and /games/345. The long ids (a user's uuid, a game's Durable Object id)
// stay the keys everywhere else; the tables user_nums and game_nums (apps/worker/migrations/0008_numeric_ids.sql) say which number is which id. A number is
// given once, in the order things were made, and never given again.
import type { Db } from "./db";

const CHUNK = 40; // D1 takes a limited number of values in one statement

/** A number in an address: a whole number from 1 (nothing else: "12abc", "0", "-3" and "1.5" are not numbers). */
export function parseNum(text: string): number | null {
  return /^[1-9][0-9]{0,9}$/.test(text) ? Number(text) : null;
}

/** The long id of a game: 64 hexadecimal characters (a Durable Object id), the form of the addresses before the numbers. */
export const isGameHex = (text: string): boolean => /^[0-9a-f]{64}$/.test(text);

/** The old form of a user id: a uuid, or `guest-` and a uuid. */
export const isUserUuid = (text: string): boolean => /^(guest-)?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(text);

type Kind = { table: "user_nums" | "game_nums"; key: "user_id" | "game_id" };
const USERS: Kind = { table: "user_nums", key: "user_id" };
const GAMES: Kind = { table: "game_nums", key: "game_id" };

/** The number of an id, given when there is none yet. */
async function numOf(db: Db, kind: Kind, id: string): Promise<number> {
  const have = await db.all<{ num: number }>(`SELECT num FROM ${kind.table} WHERE ${kind.key} = ?`, id);
  if (have[0]) return have[0].num;
  await db.run(
    `INSERT INTO ${kind.table} (${kind.key}) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM ${kind.table} WHERE ${kind.key} = ?)`,
    id,
    id,
  );
  const now = await db.all<{ num: number }>(`SELECT num FROM ${kind.table} WHERE ${kind.key} = ?`, id);
  return (now[0] as { num: number }).num;
}

async function idOf(db: Db, kind: Kind, num: number): Promise<string | null> {
  const rows = await db.all<{ id: string }>(`SELECT ${kind.key} AS id FROM ${kind.table} WHERE num = ?`, num);
  return rows[0]?.id ?? null;
}

/** The numbers of many ids at once (ids that have none are given one when `create` is set). */
async function numsOf(db: Db, kind: Kind, ids: string[], create: boolean): Promise<Map<string, number>> {
  const out = new Map<string, number>();
  const unique = [...new Set(ids)];
  for (let i = 0; i < unique.length; i += CHUNK) {
    const part = unique.slice(i, i + CHUNK);
    const rows = await db.all<{ id: string; num: number }>(
      `SELECT ${kind.key} AS id, num FROM ${kind.table} WHERE ${kind.key} IN (${part.map(() => "?").join(", ")})`,
      ...part,
    );
    for (const r of rows) out.set(r.id, r.num);
  }
  if (create) for (const id of unique) if (!out.has(id)) out.set(id, await numOf(db, kind, id));
  return out;
}

export const userNum = (db: Db, userId: string): Promise<number> => numOf(db, USERS, userId);
export const userIdOfNum = (db: Db, num: number): Promise<string | null> => idOf(db, USERS, num);
/** The numbers of players (every id gets one: a player who has none yet is numbered now). */
export const userNums = (db: Db, ids: string[]): Promise<Map<string, number>> => numsOf(db, USERS, ids, true);

export const gameNum = (db: Db, gameId: string): Promise<number> => numOf(db, GAMES, gameId);
export const gameIdOfNum = (db: Db, num: number): Promise<string | null> => idOf(db, GAMES, num);
export const gameNums = (db: Db, ids: string[]): Promise<Map<string, number>> => numsOf(db, GAMES, ids, true);

/**
 * The long id of the game that an address names: its number, or (an address from before the numbers) the long id itself. `redirect` is the number to
 * send an old address to, so that one game has one address.
 */
export async function resolveGame(db: Db, param: string): Promise<{ id: string; redirect: number | null } | null> {
  const n = parseNum(param);
  if (n !== null) {
    const id = await gameIdOfNum(db, n);
    return id === null ? null : { id, redirect: null };
  }
  if (isGameHex(param)) return { id: param, redirect: await gameNum(db, param) };
  return null;
}

/** The same for a player: a number, or the old uuid address. */
export async function resolveUser(db: Db, param: string): Promise<{ id: string; redirect: number | null } | null> {
  const n = parseNum(param);
  if (n !== null) {
    const id = await userIdOfNum(db, n);
    return id === null ? null : { id, redirect: null };
  }
  if (isUserUuid(param)) return { id: param, redirect: await userNum(db, param) };
  return null;
}
