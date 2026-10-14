// Decisions D24 (kick, rated games of any length), D25 (the archive of every game) and D26 (clock speeds).
import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { type ReplayFile, actionPath, headerPath, replayPath, resultPath } from "../src/core/archive.js";
import * as clocks from "../src/core/clock.js";
import { EngineArchive } from "../src/core/engineArchive.js";
import { shuffledSeats } from "../src/core/seating.js";
import { alice, bob, cy, makeRoom } from "./helpers.js";

// the games of these tests start at the time 1_000_000 of the test clock
const G3 = { id: "g3", createdAt: 1_000_000, startedAt: 1_000_000 };
const three = { players: 3 } as Options;
const bank = { kind: "bank", initialMs: 10_000, incrementMs: 1000 } as const;

async function trio(clock: clocks.ClockSettings = bank, rated = true) {
  const t = makeRoom({ last: 1000 });
  await t.room.init("g3", three, clock, rated, alice);
  await t.room.join(bob);
  await t.room.join(cy);
  return t;
}

describe("kick (D24)", () => {
  it("a clock running out does not end a game of 3 players, and sets no alarm", async () => {
    const t = await trio();
    expect(t.alarms.at(-1)).toBeNull();
    t.advance(60_000);
    await t.room.onAlarm();
    expect((await t.room.meta())?.status).toBe("playing");
  });

  it("another player can kick a player whose clock is negative: the others share first place", async () => {
    const t = await trio();
    t.advance(10_001); // alice is on the clock and out of time
    expect((await t.room.kick(bob, 0)).ok).toBe(true);
    const meta = await t.room.meta();
    expect(meta?.status).toBe("finished");
    expect(meta?.result).toMatchObject({ reason: "kicked", forfeit: 0, winners: [1, 2] });
    expect(meta?.result?.ranking.map((r) => r.rank)).toEqual([2, 1, 1]);
    expect(t.sink.ends[0]?.rec.rated).toBe(true);
  });

  it("refuses when the clock is not negative, for yourself, in 2-player games and for non-players", async () => {
    const t = await trio();
    expect(await t.room.kick(bob, 0)).toMatchObject({ ok: false, code: "not_overdue" });
    t.advance(20_000);
    expect(await t.room.kick(alice, 0)).toMatchObject({ ok: false, code: "bad_target" });
    const two = makeRoom({ last: 1000 });
    await two.room.init("g", { players: 2 } as Options, bank, false, alice);
    await two.room.join(bob);
    two.advance(20_000);
    expect(await two.room.kick(bob, 0)).toMatchObject({ ok: false, code: "no_kick" });
  });

  it("a negative bank stays negative after the player acts (the increment does not wipe it out)", () => {
    let c = clocks.start(clocks.initialClock(bank, 3), 0, 0);
    c = clocks.stop(bank, c, 15_000);
    expect(c.bank[0]).toBe(-4000);
    expect(clocks.overdue(bank, c, 15_000, 0)).toBe(true);
  });
});

describe("clock speeds (D26)", () => {
  it("the starting time is also the most a bank can hold", () => {
    let c = clocks.start(clocks.initialClock(bank, 2), 0, 0);
    c = clocks.stop(bank, c, 200); // would be 10_000 - 200 + 1000
    expect(c.bank[0]).toBe(10_000);
  });
});

describe("rated games have no minimum length (D24)", () => {
  it("a resignation before any action counts", async () => {
    const t = makeRoom({ last: 1000 });
    await t.room.init("g", { players: 2 } as Options, { kind: "none" }, true, alice);
    await t.room.join(bob);
    await t.room.resign(alice);
    expect(t.sink.ends[0]?.rec.rated).toBe(true);
  });
});

describe("the seed stays secret while the game is on (rule 6)", () => {
  it("publicMeta has no seed until the game is over; the replay file only exists then", async () => {
    const t = await trio({ kind: "none" });
    expect((await t.room.publicMeta())?.options.seed).toBeUndefined();
    expect(await t.room.replayFile()).toBeNull();
    await t.room.resign(alice);
    expect((await t.room.publicMeta())?.options.seed).toBe(4242);
    expect((await t.room.replayFile())?.actions).toEqual([]);
  });
});

describe("one move at a time", () => {
  it("two identical messages sent together make one move", async () => {
    const t = makeRoom({ last: 1000 });
    await t.room.init("g", { players: 2 } as Options, { kind: "none" }, false, alice);
    await t.room.join(bob);
    const [a, b] = await Promise.all([t.room.submit(alice, 0, { type: "score" }), t.room.submit(alice, 0, { type: "score" })]);
    expect([a.ok, b.ok].filter(Boolean)).toHaveLength(1);
    expect(await t.room.log()).toHaveLength(1);
  });
});

describe("the archive (D25)", () => {
  it("files go under seti-engine/games/YYYY/MM/DD/<id>/ (the day the game started, UTC)", () => {
    expect(headerPath({ id: "abc", createdAt: 0, startedAt: Date.UTC(2026, 9, 13, 23, 59) })).toBe(
      "seti-engine/games/2026/10/13/abc/header.json",
    );
    expect(actionPath({ id: "abc", createdAt: 0, startedAt: Date.UTC(2026, 0, 2) }, 42)).toBe(
      "seti-engine/games/2026/01/02/abc/actions/0000042.json",
    );
  });

  it("logs the header, every action and the result of a finished game", async () => {
    const t = await trio({ kind: "none" }, false);
    await t.room.submit(alice, 0, { type: "score" });
    await t.room.submit(bob, 1, { type: "score" });
    await t.room.resign(cy);
    await t.room.archived();
    const f = t.archive.files;
    expect(f.get(headerPath(G3))).toMatchObject({
      format: "seti-game-log/1",
      options: { seed: 4242 },
      seats: [{ userId: "u-alice" }, {}, {}],
    });
    expect(f.get(actionPath(G3, 0))).toMatchObject({ seat: 0, action: { type: "score" } });
    expect(f.has(actionPath(G3, 1))).toBe(true);
    expect(f.get(resultPath(G3))).toMatchObject({ status: "finished", result: { reason: "resigned" } });
    const replay = f.get(replayPath(G3)) as ReplayFile;
    expect(replay.actions).toHaveLength(2);
    expect(replay.result?.result.forfeit).toBe(2);
  });

  it("logs a game that never ends as it is played", async () => {
    const t = await trio({ kind: "none" }, false);
    await t.room.submit(alice, 0, { type: "score" });
    await t.room.archived();
    expect(t.archive.files.has(headerPath(G3))).toBe(true);
    expect(t.archive.files.has(actionPath(G3, 0))).toBe(true);
    expect(t.archive.files.has(replayPath(G3))).toBe(false);
  });

  it("retries after a failure without losing or repeating anything", async () => {
    const t = await trio({ kind: "none" }, false);
    t.archive.failing = true;
    await t.room.submit(alice, 0, { type: "score" });
    await t.room.archived();
    expect(t.archive.files.size).toBe(0);
    t.archive.failing = false;
    await t.room.submit(bob, 1, { type: "score" });
    await t.room.resign(cy);
    await t.room.archived();
    expect([...t.archive.files.keys()].sort()).toEqual(
      [headerPath(G3), actionPath(G3, 0), actionPath(G3, 1), resultPath(G3), replayPath(G3)].sort(),
    );
  });

  it("asks for a new try in a minute when the end of the game cannot be archived", async () => {
    const t = await trio({ kind: "none" }, false);
    t.archive.failing = true;
    await t.room.resign(alice);
    await t.room.archived();
    expect(t.alarms.at(-1)).toBe(t.clock() + 60_000);
    t.archive.failing = false;
    await t.room.onAlarm();
    await t.room.archived();
    expect(t.archive.files.has(replayPath(G3))).toBe(true);
  });
});

describe("the archive writer", () => {
  it("sends each file to the engine service, which holds the Google credentials", async () => {
    const calls: { url: string; method: string; body: unknown; auth: string | null }[] = [];
    const fetcher = (async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({
        url: String(input),
        method: String(init?.method),
        body: JSON.parse(String(init?.body)),
        auth: new Headers(init?.headers).get("authorization"),
      });
      return new Response("{}", { status: calls.length === 2 ? 503 : 200 });
    }) as typeof fetch;
    const a = new EngineArchive("https://engine.example", fetcher, async () => ({ authorization: "Bearer t" }));
    await a.put("seti-engine/games/2026/10/13/g/header.json", { x: 1 });
    expect(calls[0]).toEqual({
      url: "https://engine.example/archive",
      method: "PUT",
      body: { path: "seti-engine/games/2026/10/13/g/header.json", body: { x: 1 } },
      auth: "Bearer t",
    });
    await expect(a.put("p", {})).rejects.toThrow("503");
  });
});

describe("seating (D28)", () => {
  it("the seats are drawn when the game starts: the host is not always in seat 0, and the draw follows the seed", async () => {
    const hostSeats = new Set<number>();
    for (let seed = 1; seed <= 40; seed++) {
      const t = makeRoom({ last: 1000, seed });
      await t.room.init("g", three, { kind: "none" }, false, alice);
      await t.room.join(bob);
      await t.room.join(cy);
      const meta = await t.room.meta();
      hostSeats.add(meta?.seats.findIndex((s) => s?.id === alice.id) ?? -1);
      expect(meta?.seats.map((s) => s?.id).sort()).toEqual([alice.id, bob.id, cy.id]);
    }
    expect(shuffledSeats([1, 2, 3, 4], 77)).toEqual(shuffledSeats([1, 2, 3, 4], 77));
    expect(new Set([1, 2, 3, 4, 5, 6, 7, 8].map((seed) => shuffledSeats([0, 1, 2], seed)[0])).size).toBe(3);
    expect(hostSeats).toEqual(new Set([0, 1, 2])); // over 40 games the host sat in every seat
  });

  it("the host id stays the host after the draw", async () => {
    const t = await trio({ kind: "none" }, false);
    expect((await t.room.meta())?.host).toBe(alice.id);
  });
});

describe("abandoned lobbies (D27)", () => {
  const four = { players: 4 } as Options;

  it("a lobby whose players stop pinging is emptied and destroyed", async () => {
    const t = makeRoom();
    await t.room.init("g", four, { kind: "none" }, false, alice);
    await t.room.join(bob);
    expect(t.alarms.at(-1)).toBe(t.clock() + 20_000);
    t.advance(30_000);
    await t.room.onAlarm();
    expect((await t.room.meta())?.status).toBe("lobby"); // not a minute yet
    t.advance(31_000);
    await t.room.onAlarm();
    expect(await t.room.meta()).toBeUndefined();
    expect(t.sink.removed).toEqual(["g"]);
  });

  it("a player who keeps pinging stays; the one who stopped is dropped and the host passes on", async () => {
    const t = makeRoom();
    await t.room.init("g", four, { kind: "none" }, false, alice);
    await t.room.join(bob);
    await t.room.join(cy);
    for (let i = 0; i < 5; i++) {
      t.advance(15_000);
      await t.room.touch(bob);
      await t.room.touch(cy);
    }
    await t.room.onAlarm();
    const meta = await t.room.meta();
    expect(meta?.joined).toEqual([bob.id, cy.id]);
    expect(meta?.host).toBe(bob.id);
    expect(t.alarms.at(-1)).toBe(t.clock() + 20_000);
  });

  it("a game that has started no longer cares about pings", async () => {
    const t = makeRoom({ last: 1000 });
    await t.room.init("g", { players: 2 } as Options, { kind: "none" }, false, alice);
    await t.room.join(bob);
    t.advance(10 * 60_000);
    await t.room.onAlarm();
    expect((await t.room.meta())?.status).toBe("playing");
  });
});
