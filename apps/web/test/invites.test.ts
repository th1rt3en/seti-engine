import { describe, expect, it } from "vitest";
import { SqliteDb, migrationSql } from "../src/lib/db";
import { findPlayers, pendingInvites } from "../src/lib/invites";

async function world() {
  const db = new SqliteDb(":memory:", migrationSql());
  const user = (id: string, name: string, guest = 0) =>
    db.run("INSERT INTO users (id, name, is_guest, created_at) VALUES (?, ?, ?, 1)", id, name, guest);
  await user("u1", "Alice");
  await user("u2", "Bob");
  await user("u3", "Bobby");
  await user("u4", "Rob_ert");
  await user("u5", "Abby");
  await user("g1", "Bobguest", 1);
  await db.run("INSERT INTO user_nums (user_id) VALUES ('u2')");
  return db;
}

describe("finding a player to invite", () => {
  it("matches part of the username in any case, puts the names that begin with it first, and leaves out guests and the host", async () => {
    const db = await world();
    expect((await findPlayers(db, "b", "u1")).map((p) => p.name)).toEqual(["Bob", "Bobby", "Abby", "Rob_ert"]);
    expect((await findPlayers(db, "ALI", "u2")).map((p) => p.name)).toEqual(["Alice"]);
    expect(await findPlayers(db, "ali", "u1")).toEqual([]); // not the host themselves
    expect((await findPlayers(db, "bobg", "u1")).length).toBe(0); // a guest is not a registered player
  });

  it("gives the number of the player's page, and treats % and _ as plain characters", async () => {
    const db = await world();
    expect(await findPlayers(db, "Bob", "u1", 1)).toEqual([{ name: "Bob", num: 1 }]);
    expect(await findPlayers(db, "%", "u1")).toEqual([]);
    expect((await findPlayers(db, "b_r", "u1")).length).toBe(0);
    expect((await findPlayers(db, "_", "u1")).map((p) => p.name)).toEqual(["Rob_ert"]);
    expect(await findPlayers(db, "   ", "u1")).toEqual([]);
  });
});

describe("the invitations that wait for a player", () => {
  it("lists the pending ones to tables that are lobbies, with the number of the game, and nothing else", async () => {
    const db = await world();
    await db.run("INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES ('ga', 'lobby', '{}', '{}', 0, 1)");
    await db.run("INSERT INTO games (id, status, options_json, clock_json, rated, created_at) VALUES ('gb', 'playing', '{}', '{}', 0, 1)");
    await db.run("INSERT INTO game_nums (game_id) VALUES ('ga')");
    const invite = (game: string, seat: number, user: string, status: string) =>
      db.run("INSERT INTO lobby_invites VALUES (?, ?, ?, 'x', 'Alice', ?, ?)", game, seat, user, status, 10 + seat);
    await invite("ga", 1, "u2", "pending");
    await invite("ga", 2, "u3", "pending"); // another player's
    await invite("gb", 1, "u2", "pending"); // the game has started
    await invite("ga", 3, "u2", "declined"); // answered
    expect(await pendingInvites(db, "u2")).toEqual([{ gameId: "ga", num: 1, seat: 1, host: "Alice", at: 11 }]);
    expect(await pendingInvites(db, "u4")).toEqual([]);
  });
});
