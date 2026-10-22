import { describe, expect, it } from "vitest";
import { SqliteDb, migrationSql } from "../src/lib/db";
import { gameIdOfNum, gameNum, gameNums, isGameHex, parseNum, resolveGame, resolveUser, userNum, userNums } from "../src/lib/ids";

const memory = () => new SqliteDb(":memory:", migrationSql());
const HEX = "ab".repeat(32);
const UUID = "0b9a6c54-1a3c-4b6e-9c1e-2f3d4e5f6a7b";

describe("the numbers of players and games", () => {
  it("accepts only whole numbers in an address", () => {
    expect(parseNum("12")).toBe(12);
    for (const bad of ["0", "-3", "1.5", "12abc", "", " 4", "00", "99999999999"]) expect(parseNum(bad)).toBeNull();
    expect(isGameHex(HEX)).toBe(true);
    expect(isGameHex(HEX.slice(1))).toBe(false);
  });

  it("gives a number once, in order, and the same one every time", async () => {
    const db = memory();
    expect(await userNum(db, "u-a")).toBe(1);
    expect(await userNum(db, "u-b")).toBe(2);
    expect(await userNum(db, "u-a")).toBe(1);
    const many = await userNums(db, ["u-b", "u-c", "u-a", "u-c"]);
    expect([...many.entries()].sort()).toEqual([
      ["u-a", 1],
      ["u-b", 2],
      ["u-c", 3],
    ]);
  });

  it("numbers the games apart from the players, and does not reuse a number of a deleted game", async () => {
    const db = memory();
    expect(await gameNum(db, "g1")).toBe(1);
    expect(await gameNum(db, "g2")).toBe(2);
    await db.run("DELETE FROM game_nums WHERE game_id = 'g2'"); // not what happens in use (the number stays); the key never goes back anyway
    expect(await gameNum(db, "g3")).toBe(3);
    expect((await gameNums(db, ["g1", "g3"])).get("g3")).toBe(3);
    expect(await gameIdOfNum(db, 1)).toBe("g1");
    expect(await gameIdOfNum(db, 2)).toBeNull();
  });

  it("finds the game or the player of an address, and says where an old address goes", async () => {
    const db = memory();
    const n = await gameNum(db, HEX);
    expect(await resolveGame(db, String(n))).toEqual({ id: HEX, redirect: null });
    expect(await resolveGame(db, HEX)).toEqual({ id: HEX, redirect: n });
    expect(await resolveGame(db, "999")).toBeNull();
    expect(await resolveGame(db, "not-an-id")).toBeNull();
    const u = await userNum(db, UUID);
    expect(await resolveUser(db, String(u))).toEqual({ id: UUID, redirect: null });
    expect(await resolveUser(db, UUID)).toEqual({ id: UUID, redirect: u });
    expect(await resolveUser(db, "7")).toBeNull();
  });

  it("numbers the games and players that existed before, in the order they were made", async () => {
    // the migration numbers what is already there: the players are put in between the earlier migrations and the one of the numbers
    const all = migrationSql();
    const before = all.slice(0, -1);
    const existing =
      "INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES ('late', 'Late', NULL, NULL, 0, 20);" +
      "INSERT INTO users (id, name, email, password_hash, is_guest, created_at) VALUES ('early', 'Early', NULL, NULL, 0, 10);";
    const db = new SqliteDb(":memory:", [...before, existing, all.at(-1) as string]);
    expect(await userNum(db, "early")).toBe(1);
    expect(await userNum(db, "late")).toBe(2);
  });
});
