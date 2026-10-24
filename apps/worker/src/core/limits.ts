// How many tables (lobbies and games in progress) one player can have open at a time. A guest has one; an account has ten. A table that is finished,
// cancelled or never started does not count. The Worker asks before it makes a table or seats a player (worker.ts).
export const GUEST_TABLE_LIMIT = 1;
export const ACCOUNT_TABLE_LIMIT = 10;

export const tableLimit = (registered: boolean): number => (registered ? ACCOUNT_TABLE_LIMIT : GUEST_TABLE_LIMIT);

/** The answer to a player who would go over the limit, or null when the table can be made or joined. `open` is how many tables the player has open now. */
export function overTableLimit(registered: boolean, open: number): { ok: false; code: "table_limit"; message: string } | null {
  const limit = tableLimit(registered);
  if (open < limit) return null;
  const finish = `You must finish your tables before creating or joining a new one. You can have ${limit} table${limit === 1 ? "" : "s"} open at a time (a lobby or a game in progress). You can resign your solo tables from your profile without any repercussion.`;
  const guest = registered
    ? ""
    : ` As a guest you can have ${GUEST_TABLE_LIMIT} table open: create an account to have up to ${ACCOUNT_TABLE_LIMIT} open tables.`;
  return { ok: false, code: "table_limit", message: finish + guest };
}
