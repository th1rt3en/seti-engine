import { SignJWT, exportSPKI, generateKeyPair } from "jose";
import { describe, expect, it } from "vitest";
import { AuthError, verifyToken } from "../src/core/auth.js";
import * as clocks from "../src/core/clock.js";
import { FLOOR, START_RATING, applyDeltas, deltas, expected, kFor } from "../src/core/elo.js";
import { rank } from "../src/core/room.js";

describe("Elo (docs/PLAN.md section 6)", () => {
  it("2 players: standard Elo", () => {
    const d = deltas([
      { id: "a", rating: 1500, rank: 1 },
      { id: "b", rating: 1500, rank: 2 },
    ]);
    expect(d.get("a")).toBeCloseTo(10);
    expect(d.get("b")).toBeCloseTo(-10);
  });

  it("an upset moves more than an expected win", () => {
    const upset = deltas([
      { id: "low", rating: 1300, rank: 1 },
      { id: "high", rating: 1700, rank: 2 },
    ]);
    const normal = deltas([
      { id: "low", rating: 1300, rank: 2 },
      { id: "high", rating: 1700, rank: 1 },
    ]);
    expect(upset.get("low")).toBeGreaterThan(18);
    expect(normal.get("high")).toBeLessThan(2);
  });

  it("a tie is a draw: equal ratings do not move", () => {
    const d = deltas([
      { id: "a", rating: 1500, rank: 1 },
      { id: "b", rating: 1500, rank: 1 },
    ]);
    expect(d.get("a")).toBeCloseTo(0);
  });

  it("3 and 4 players: pairwise, one game moves a rating by at most K and the total stays zero", () => {
    for (const n of [3, 4]) {
      const players = Array.from({ length: n }, (_, i) => ({ id: `p${i}`, rating: 1500 + 40 * i, rank: i + 1 }));
      const d = deltas(players);
      expect(Math.max(...[...d.values()].map(Math.abs))).toBeLessThanOrEqual(20);
      expect([...d.values()].reduce((a, b) => a + b, 0)).toBeCloseTo(0);
    }
    const winner = deltas([
      { id: "w", rating: 1500, rank: 1 },
      { id: "x", rating: 1500, rank: 2 },
      { id: "y", rating: 1500, rank: 3 },
    ]);
    expect(winner.get("w")).toBeCloseTo(10); // wins both pairs: 2 * (K / 2) * 0.5
    expect(winner.get("x")).toBeCloseTo(0);
    expect(winner.get("y")).toBeCloseTo(-10);
  });

  it("rounds the new ratings", () => {
    const r = applyDeltas([
      { id: "a", rating: START_RATING, rank: 1, games: 0 },
      { id: "b", rating: START_RATING, rank: 2, games: 0 },
    ]);
    expect(r.get("a")).toBe(30); // everybody starts at 0, and a new player has K = 60
    expect(r.get("b")).toBe(0); // below 100: nothing is lost
    expect(expected(1500, 1500)).toBeCloseTo(0.5);
  });

  it("K is 60 for the first 10 rated games, 40 for the next 10, then 20", () => {
    expect([0, 9, 10, 19, 20, 99].map(kFor)).toEqual([60, 60, 40, 40, 20, 20]);
    const at = (games: number) =>
      deltas([
        { id: "a", rating: 1500, rank: 1, games },
        { id: "b", rating: 1500, rank: 2, games: 30 },
      ]).get("a");
    expect(at(0)).toBeCloseTo(30);
    expect(at(10)).toBeCloseTo(20);
    expect(at(20)).toBeCloseTo(10);
  });

  it("nobody drops below 100, a player below 100 loses nothing, and the winner gains as usual", () => {
    const r = applyDeltas([
      { id: "high", rating: 1500, rank: 1, games: 30 },
      { id: "low", rating: 50, rank: 2, games: 30 },
    ]);
    expect(r.get("low")).toBe(50); // below the floor: no loss
    expect(r.get("high")).toBe(1500); // the favourite wins, so a small gain (rounded)
    const upset = applyDeltas([
      { id: "low", rating: 0, rank: 1, games: 0 },
      { id: "high", rating: 1500, rank: 2, games: 30 },
    ]);
    expect(upset.get("low")).toBe(60); // a win over a strong player at K = 60
    expect(upset.get("high")).toBe(1480); // and the strong player loses as usual (K = 20)
    const near = applyDeltas([
      { id: "a", rating: 105, rank: 2, games: 30 },
      { id: "b", rating: 105, rank: 1, games: 30 },
    ]);
    expect(near.get("a")).toBe(FLOOR); // 105 - 10 would be 95: the floor holds it at 100
    expect(near.get("b")).toBe(115);
  });
});

describe("clocks (decision D13)", () => {
  it("per-turn clock: the deadline is a fixed time after the turn began", () => {
    const s: clocks.ClockSettings = { kind: "per_turn", ms: 1000 };
    const c = clocks.start(clocks.initialClock(s, 2), 1, 5000);
    expect(clocks.deadline(s, c)).toBe(6000);
    expect(clocks.expired(s, c, 5999)).toBeNull();
    expect(clocks.expired(s, c, 6000)).toBe(1);
  });

  it("bank clock: time is taken from the bank and the increment is added when the player acts", () => {
    const s: clocks.ClockSettings = { kind: "bank", initialMs: 10_000, incrementMs: 2000 };
    let c = clocks.start(clocks.initialClock(s, 2), 0, 0);
    expect(clocks.deadline(s, c)).toBe(10_000);
    c = clocks.stop(s, c, 3000);
    expect(c.bank).toEqual([9000, 10_000]);
    c = clocks.start(c, 1, 3000);
    expect(clocks.remaining(s, c, 5000, 2)).toEqual([9000, 8000]);
  });

  it("an untimed game never expires", () => {
    const s: clocks.ClockSettings = { kind: "none" };
    const c = clocks.start(clocks.initialClock(s, 2), 0, 0);
    expect(clocks.deadline(s, c)).toBeNull();
    expect(clocks.remaining(s, c, 99, 2)).toBeNull();
  });
});

describe("ranking", () => {
  it("equal scores share a rank; a forfeit is last", () => {
    expect(rank([10, 30, 10]).map((r) => r.rank)).toEqual([2, 1, 2]);
    expect(rank([10, 30, 20], 1).map((r) => r.rank)).toEqual([2, 3, 1]);
  });
});

describe("tokens (decision D16)", () => {
  async function setup() {
    const { publicKey, privateKey } = await generateKeyPair("ES256");
    const pem = await exportSPKI(publicKey);
    const sign = (claims: Record<string, unknown>, aud = "seti-worker", exp = "5m") =>
      new SignJWT(claims)
        .setProtectedHeader({ alg: "ES256" })
        .setIssuer("site")
        .setAudience(aud)
        .setSubject("u1")
        .setExpirationTime(exp)
        .sign(privateKey);
    return { pem, sign };
  }

  it("accepts a valid token and reads the identity", async () => {
    const { pem, sign } = await setup();
    const id = await verifyToken(await sign({ name: "Ann", reg: true }), { publicKeyPem: pem, issuer: "site", audience: "seti-worker" });
    expect(id).toEqual({ id: "u1", name: "Ann", registered: true });
    const g = await verifyToken(await sign({}), { publicKeyPem: pem, issuer: "site", audience: "seti-worker" });
    expect(g).toEqual({ id: "u1", name: "Guest", registered: false });
  });

  it("refuses a wrong audience, a wrong key and an expired token", async () => {
    const { pem, sign } = await setup();
    const other = await setup();
    const cfg = { publicKeyPem: pem, issuer: "site", audience: "seti-worker" };
    await expect(verifyToken(await sign({}, "someone-else"), cfg)).rejects.toBeInstanceOf(AuthError);
    await expect(verifyToken(await other.sign({}), cfg)).rejects.toBeInstanceOf(AuthError);
    await expect(verifyToken(await sign({}, "seti-worker", "-1m"), cfg)).rejects.toBeInstanceOf(AuthError);
    await expect(verifyToken("not.a.token", cfg)).rejects.toBeInstanceOf(AuthError);
  });
});
