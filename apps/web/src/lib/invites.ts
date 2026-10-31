// The invitations to a lobby. The room owns them (apps/worker/src/core/room.ts); the Worker copies them to the table lobby_invites, which the site
// reads here: to tell an invited player, wherever they are on the site, and to find the registered players that the host can invite.
import type { Db } from "./db";

export interface PendingInvite {
  /** The long id of the game (the Worker's routes take it). */
  gameId: string;
  /** The number in the address of the game's page. */
  num: number | null;
  seat: number;
  host: string;
  at: number;
}

/** The invitations that wait for an answer from this player, newest first, to tables that are still lobbies. */
export async function pendingInvites(db: Db, userId: string): Promise<PendingInvite[]> {
  const rows = await db.all<{ game_id: string; num: number | null; seat: number; host_name: string; created_at: number }>(
    `SELECT i.game_id AS game_id, gn.num AS num, i.seat AS seat, i.host_name AS host_name, i.created_at AS created_at
     FROM lobby_invites i JOIN games g ON g.id = i.game_id LEFT JOIN game_nums gn ON gn.game_id = i.game_id
     WHERE i.user_id = ? AND i.status = 'pending' AND g.status = 'lobby' ORDER BY i.created_at DESC LIMIT 5`,
    userId,
  );
  return rows.map((r) => ({ gameId: r.game_id, num: r.num, seat: r.seat, host: r.host_name, at: r.created_at }));
}

export interface FoundPlayer {
  name: string;
  num: number | null;
}

/** Registered players whose name contains `q` (guests are left out, and so is `exceptId`); the names that begin with it come first. */
export async function findPlayers(db: Db, q: string, exceptId: string, limit = 8): Promise<FoundPlayer[]> {
  const text = q.trim().slice(0, 40);
  if (text === "") return [];
  const esc = text.replace(/[\\%_]/g, (c) => `\\${c}`);
  const rows = await db.all<{ name: string; num: number | null }>(
    `SELECT u.name AS name, un.num AS num FROM users u LEFT JOIN user_nums un ON un.user_id = u.id
     WHERE u.is_guest = 0 AND u.id != ? AND u.name LIKE ? ESCAPE '\\'
     ORDER BY (u.name LIKE ? ESCAPE '\\') DESC, u.name COLLATE NOCASE LIMIT ?`,
    exceptId,
    `%${esc}%`,
    `${esc}%`,
    limit,
  );
  return rows;
}
