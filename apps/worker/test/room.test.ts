import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import type { Identity } from "../src/core/auth.js";
import type { ServerMessage } from "../src/core/room.js";
import { Conn, alice, bob, cy, guest, makeRoom } from "./helpers.js";

const two = { players: 2 } as Options;
const none = { kind: "none" } as const;

async function started(rated = false, last = 6) {
  const t = makeRoom({ last });
  await t.room.init("g1", two, none, rated, alice);
  await t.room.join(bob);
  await t.room.startGame(alice); // the host starts the game once the lobby is full
  return t;
}

function viewOf(c: Conn): { seq: number; view: { to_act: number | null; state: { played: number } } } {
  return c.last("view") as never;
}

describe("lobby", () => {
  it("starts when every seat is taken, with a seed chosen by the room", async () => {
    const t = makeRoom();
    await t.room.init("g1", two, none, false, alice);
    expect((await t.room.meta())?.status).toBe("lobby");
    const j = await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    expect(j).toMatchObject({ ok: true, seat: 1 });
    const meta = await t.room.meta();
    expect(meta?.status).toBe("playing");
    expect(meta?.options.seed).toBe(4242);
    expect(t.sink.starts).toHaveLength(1);
  });

  it("joining again returns the same seat; a full or started game refuses", async () => {
    const t = await started();
    expect(await t.room.join(bob)).toMatchObject({ ok: true, seat: 1 });
    expect(await t.room.join(cy)).toMatchObject({ ok: false, code: "started" });
  });

  it("rated games need registered players and 2 to 4 seats", async () => {
    const t = makeRoom();
    expect(await t.room.init("g", { players: 1 } as Options, none, true, alice)).toMatchObject({ ok: false, code: "not_rateable" });
    expect(await t.room.init("g", two, none, true, guest)).toMatchObject({ ok: false, code: "guest" });
    expect((await t.room.init("g", two, none, true, alice)).ok).toBe(true);
    expect(await t.room.join(guest)).toMatchObject({ ok: false, code: "guest" });
  });

  it("a solo game starts at once", async () => {
    const t = makeRoom();
    await t.room.init("g", { players: 1 } as Options, none, false, alice);
    expect((await t.room.meta())?.status).toBe("playing");
  });

  it("a player can leave the lobby; the last one to leave destroys it (D27)", async () => {
    const t = makeRoom();
    const c = new Conn("c", null);
    t.conns.push(c);
    await t.room.init("g", { players: 3 } as Options, none, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    expect(await t.room.leave(bob)).toEqual({ ok: true });
    expect((await t.room.meta())?.seats[1]).toBeNull();
    await t.room.leave(alice);
    expect(await t.room.meta()).toBeUndefined(); // everything is forgotten: a link to it leads nowhere
    expect(t.store.data.size).toBe(0);
    expect(t.sink.removed).toEqual(["g"]);
    expect(await t.room.join(cy)).toMatchObject({ ok: false, code: "unknown_game" });
    expect(c.last("lobby")).toMatchObject({ status: "cancelled" });
  });

  it("the creator is the host; when the host leaves, the player who joined next is the host (D27)", async () => {
    const t = makeRoom();
    await t.room.init("g", { players: 4 } as Options, none, false, alice);
    expect((await t.room.meta())?.host).toBe(alice.id);
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    await t.room.join(cy);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    await t.room.leave(alice);
    expect((await t.room.meta())?.host).toBe(bob.id);
    await t.room.leave(bob);
    expect((await t.room.meta())?.host).toBe(cy.id);
    // a player who rejoins goes to the back of the line
    await t.room.join(alice);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    await t.room.leave(cy);
    const meta = await t.room.meta();
    expect(meta?.host).toBe(alice.id);
    expect(meta?.status).toBe("lobby");
  });

  it("the lobby message names the host", async () => {
    const t = makeRoom();
    const c = new Conn("c", null);
    t.conns.push(c);
    await t.room.init("g", { players: 3 } as Options, none, false, alice);
    expect(c.last("lobby")).toMatchObject({ host: "Alice" });
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    await t.room.leave(alice);
    expect(c.last("lobby")).toMatchObject({ host: "Bob" });
  });
});

describe("play", () => {
  it("applies an action through the engine, logs it and tells everyone their own view", async () => {
    const t = await started();
    const a = new Conn("a", alice.id);
    const b = new Conn("b", bob.id);
    const s = new Conn("s", null);
    t.conns.push(a, b, s);
    expect(await t.room.submit(alice, 0, { type: "score" })).toEqual({ ok: true });
    expect(viewOf(a).seq).toBe(1);
    expect(viewOf(a).view.state.played).toBe(1);
    expect(viewOf(b).view.to_act).toBe(1);
    expect((viewOf(a).view as unknown as { legal: unknown[] }).legal).toEqual([]); // not Alice's turn any more
    expect((viewOf(b).view as unknown as { legal: unknown[] }).legal).toEqual([{ type: "score" }]);
    expect((viewOf(s).view as unknown as { viewer: unknown }).viewer).toBeNull();
    const log = await t.room.log();
    expect(log).toHaveLength(1);
    expect(log[0]).toMatchObject({ seq: 0, seat: 0, action: { type: "score" } });
  });

  it("tells the players' numbers with their names, seat by seat (null for a player without one)", async () => {
    const t = makeRoom();
    await t.room.init("g1", two, none, false, { ...alice, num: 7 });
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    const s = new Conn("s", null);
    t.conns.push(s);
    await t.room.submit({ ...alice, num: 7 }, 0, { type: "score" }).catch(() => undefined); // any move makes the room send the view
    const v = s.last("view") as unknown as { names: string[]; nums: (number | null)[] };
    expect(v.nums).toHaveLength(2);
    expect(v.nums[v.names.indexOf("Alice")]).toBe(7);
    expect(v.nums[v.names.indexOf("Bob")]).toBeNull();
    // the lobby message too
    const t2 = makeRoom();
    const c = new Conn("c", null);
    t2.conns.push(c);
    await t2.room.init("g2", two, none, false, { ...alice, num: 7 });
    expect((c.last("lobby") as unknown as { seats: ({ name: string; num?: number } | null)[] }).seats[0]).toEqual({
      name: "Alice",
      num: 7,
    });
  });

  it("refuses: not your turn, a stale count, an illegal action, a stranger", async () => {
    const t = await started();
    expect(await t.room.submit(bob, 0, { type: "score" })).toMatchObject({ ok: false, code: "not_your_turn" });
    expect(await t.room.submit(alice, 5, { type: "score" })).toMatchObject({ ok: false, code: "stale" });
    expect(await t.room.submit(alice, 0, { type: "launch" })).toMatchObject({ ok: false, code: "illegal", legal: [{ type: "score" }] });
    expect(await t.room.submit(cy, 0, { type: "score" })).toMatchObject({ ok: false, code: "not_seated" });
    expect(await t.room.log()).toHaveLength(0);
  });

  it("previews a move for the player to act without making it", async () => {
    const t = await started();
    expect(await t.room.preview(alice, { type: "score" })).toEqual({}); // the fake engine reports no change
    expect(await t.room.preview(bob, { type: "score" })).toBeNull(); // not Bob's turn
    expect(await t.room.preview(cy, { type: "score" })).toBeNull(); // not a player
    expect(await t.room.preview(alice, { type: "launch" })).toBeNull(); // an illegal move
    expect(await t.room.log()).toHaveLength(0); // nothing was played
    expect(await t.room.submit(alice, 0, { type: "score" })).toEqual({ ok: true });
  });

  it("a repeated message does not act twice", async () => {
    const t = await started();
    await t.room.submit(alice, 0, { type: "score" });
    expect(await t.room.submit(alice, 0, { type: "score" })).toMatchObject({ ok: false, code: "stale" });
    expect(await t.room.log()).toHaveLength(1);
  });

  it("a player who reconnects gets the current view", async () => {
    const t = await started();
    await t.room.submit(alice, 0, { type: "score" });
    const again = new Conn("a2", alice.id);
    await t.room.connect(again);
    expect(viewOf(again).seq).toBe(1);
  });

  it("a connecting client gets a long log in pieces that follow each other, and the next move continues it", async () => {
    const t = await started();
    for (let i = 0; i < 95; i++)
      await t.store.put(`log:${String(i).padStart(7, "0")}`, { seq: i, seat: 0, action: { type: "score" }, at: 0, events: [] });
    await t.store.put("logcount", 95);
    const c = new Conn("c", alice.id);
    await t.room.connect(c);
    const pieces = c.got.filter((m): m is Extract<ServerMessage, { t: "log" }> => m.t === "log");
    expect(pieces.map((m) => [m.from, m.entries.length])).toEqual([
      [0, 40],
      [40, 40],
      [80, 15],
    ]);
    // each piece starts where the ones before end, so the client can hold them one after the other
    expect(pieces.flatMap((m) => m.entries.map((e) => e.seq))).toEqual(Array.from({ length: 95 }, (_, i) => i));
  });

  it("connecting to a lobby shows the seats", async () => {
    const t = makeRoom();
    await t.room.init("g", { players: 3 } as Options, none, false, alice);
    const c = new Conn("c", null);
    await t.room.connect(c);
    const lobby = c.last("lobby") as Extract<ServerMessage, { t: "lobby" }>;
    expect(lobby.seats).toEqual([{ name: "Alice" }, null, null]);
  });
});

describe("the end of a game", () => {
  it("a completed game is recorded with its ranking and log", async () => {
    const t = await started(true, 4);
    for (let i = 0; i < 4; i++) {
      const who = i % 2 === 0 ? alice : bob;
      expect(await t.room.submit(who, i, { type: i === 0 ? "score" : "pass" })).toEqual({ ok: true });
    }
    expect((await t.room.meta())?.status).toBe("finished");
    const end = t.sink.ends[0];
    expect(end?.rec.result.reason).toBe("completed");
    expect(end?.rec.result.ranking.map((r) => r.rank)).toEqual([1, 2]);
    expect(end?.rec.result.winners).toEqual([0]);
    expect(end?.rec.rated).toBe(true);
    expect(end?.log).toHaveLength(4);
    expect(await t.room.submit(alice, 4, { type: "score" })).toMatchObject({ ok: false, code: "not_playing" });
  });

  it("the statistics of a completed game are made by the engine and recorded; a game that was cancelled or resigned has none", async () => {
    const t = await started(true, 4);
    for (let i = 0; i < 4; i++) await t.room.submit(i % 2 === 0 ? alice : bob, i, { type: "score" });
    await new Promise((r) => setTimeout(r, 0));
    expect(t.sink.statsRecorded).toHaveLength(1);
    expect(t.sink.statsRecorded[0]?.stats.players).toHaveLength(2);
    expect(t.sink.statsRecorded[0]?.stats.players[0]?.counters).toEqual({ "action.score": 4 });
    const u = await started(true, 4);
    await u.room.submit(alice, 0, { type: "score" });
    await u.room.resign(alice);
    await new Promise((r) => setTimeout(r, 0));
    expect(u.sink.statsRecorded).toHaveLength(0);
  });

  it("an unrated game is never rated", async () => {
    const t = await started(false, 2);
    await t.room.submit(alice, 0, { type: "score" });
    await t.room.submit(bob, 1, { type: "score" });
    expect(t.sink.ends[0]?.rec.rated).toBe(false);
  });

  it("a rated game ended by a resignation counts however short it was (decision D24)", async () => {
    const short = await started(true, 1000);
    await short.room.submit(alice, 0, { type: "score" });
    expect((await short.room.resign(bob)).ok).toBe(true);
    expect(short.sink.ends[0]?.rec).toMatchObject({ rated: true });
    expect(short.sink.ends[0]?.rec.result).toMatchObject({ reason: "resigned", forfeit: 1, winners: [0] });
    expect(short.sink.ends[0]?.rec.result.ranking.find((r) => r.seat === 1)?.rank).toBe(2);
  });

  it("a timeout makes the player on the clock lose", async () => {
    const t = makeRoom({ last: 1000 });
    await t.room.init("g", two, { kind: "per_turn", ms: 60_000 }, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    expect(t.alarms.at(-1)).toBe(t.clock() + 60_000);
    await t.room.onAlarm();
    expect((await t.room.meta())?.status).toBe("playing"); // not yet
    t.advance(60_001);
    await t.room.onAlarm();
    const meta = await t.room.meta();
    expect(meta?.status).toBe("finished");
    expect(meta?.result).toMatchObject({ reason: "timeout", forfeit: 0 });
    expect(t.alarms.at(-1)).toBeNull();
  });

  it("the clock moves to the next player after an action", async () => {
    const t = makeRoom({ last: 1000 });
    await t.room.init("g", two, { kind: "bank", initialMs: 10_000, incrementMs: 1000 }, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    t.advance(4000);
    await t.room.submit(alice, 0, { type: "score" });
    const c = new Conn("a", alice.id);
    await t.room.connect(c);
    expect((c.last("view") as Extract<ServerMessage, { t: "view" }>).remaining).toEqual([7000, 10_000]);
    expect(t.alarms.at(-1)).toBe(t.clock() + 10_000);
  });
});

describe("the lobby list", () => {
  it("tells the sink when a game is created, joined and left", async () => {
    const t = makeRoom();
    await t.room.init("g", { players: 3 } as Options, none, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice); // the host starts the game once the lobby is full
    await t.room.leave(bob);
    expect(t.sink.lobbies.map((m) => m.seats.filter((s) => s !== null).length)).toEqual([1, 2, 1]);
  });
});

describe("a failing engine", () => {
  it("keeps the lobby when the game cannot be started: the host tries again", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    await t.room.join(bob);
    const engine = (t as unknown as { room: { d: { engine: { newGame: () => Promise<never> } } } }).room.d.engine;
    const good = engine.newGame;
    engine.newGame = async () => {
      throw new Error("engine down");
    };
    await expect(t.room.startGame(alice)).rejects.toThrow("engine down");
    expect((await t.room.meta())?.status).toBe("lobby");
    expect((await t.room.meta())?.seats.every((s) => s !== null)).toBe(true);
    engine.newGame = good;
    expect(await t.room.startGame(alice)).toEqual({ ok: true });
    expect((await t.room.meta())?.status).toBe("playing");
  });
});

describe("an administrator cancels a game", () => {
  it("a rated game that is being played ends without a result, and no rating is settled", async () => {
    const t = await started(true);
    const info = await t.room.adminInfo();
    expect(info).toMatchObject({ status: "playing", rated: true, players: ["Alice", "Bob"] });
    expect(await t.room.adminCancel()).toEqual({ ok: true });
    expect((await t.room.meta())?.status).toBe("cancelled");
    expect(t.sink.cancelled).toHaveLength(1);
    expect(t.sink.ends).toHaveLength(0); // nobody wins or loses: no rating changes (the ratings are only settled by the end of a game)
    expect(await t.room.adminCancel()).toMatchObject({ ok: false, code: "not_open" });
  });

  it("a lobby is destroyed, and a finished game cannot be cancelled", async () => {
    const t = makeRoom();
    await t.room.init("g1", two, none, true, alice);
    expect((await t.room.adminInfo())?.status).toBe("lobby");
    expect(await t.room.adminCancel()).toEqual({ ok: true });
    expect(t.sink.removed).toEqual(["g1"]);
    const done = await started(false, 1);
    await done.room.resign(alice);
    expect(await done.room.adminCancel()).toMatchObject({ ok: false, code: "not_open" });
  });
});

describe("the host starts the game", () => {
  it("a full lobby waits: only the host can start it, and only when every seat is taken", async () => {
    const t = makeRoom();
    await t.room.init("g", { players: 3 } as Options, none, false, alice);
    await t.room.join(bob);
    expect(await t.room.startGame(alice)).toMatchObject({ ok: false, code: "not_full" });
    await t.room.join(cy);
    expect((await t.room.meta())?.status).toBe("lobby"); // full, and still not started
    expect(await t.room.startGame(bob)).toMatchObject({ ok: false, code: "not_host" });
    expect((await t.room.meta())?.status).toBe("lobby");
    expect(await t.room.startGame(alice)).toEqual({ ok: true });
    expect((await t.room.meta())?.status).toBe("playing");
    expect(await t.room.startGame(alice)).toMatchObject({ ok: false, code: "not_in_lobby" });
  });

  it("tells each connection the settings, the host, its own seat and whether the lobby is full", async () => {
    const t = makeRoom();
    const ca = new Conn("a", alice.id);
    const cb = new Conn("b", bob.id);
    const spec = new Conn("s", null);
    t.conns.push(ca, cb, spec);
    await t.room.init("g", { players: 2, expansion: true } as Options, none, true, alice);
    await t.room.connect(ca);
    await t.room.connect(spec);
    await t.room.join(bob);
    type Lobby = Extract<ServerMessage, { t: "lobby" }>;
    const last = (c: Conn) => c.last("lobby") as Lobby;
    expect(last(ca)).toMatchObject({ hostSeat: 0, you: 0, full: true, rated: true });
    expect(last(cb)).toMatchObject({ hostSeat: 0, you: 1, full: true });
    expect(last(spec)).toMatchObject({ you: null, full: true });
    expect(last(ca).options).toMatchObject({ players: 2, expansion: true });
    expect(last(ca).options).not.toHaveProperty("seed"); // the seed is secret
  });

  it("the host leaving gives the start to the next player", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    await t.room.join(bob);
    await t.room.leave(alice);
    expect(await t.room.startGame(alice)).toMatchObject({ ok: false });
    await t.room.join(cy);
    expect(await t.room.startGame(bob)).toEqual({ ok: true }); // bob is the host now
  });
});

describe("a seed chosen by the host", () => {
  it("is used when the game starts, only in a casual game, and only the administrator can read it", async () => {
    const t = makeRoom();
    expect(await t.room.init("r", { players: 2, seed: 77 } as Options, none, true, alice)).toMatchObject({ ok: false, code: "bad_seed" });
    const bad = makeRoom();
    expect(await bad.room.init("b", { players: 2, seed: -3 } as Options, none, false, alice)).toMatchObject({
      ok: false,
      code: "bad_seed",
    });
    const u = makeRoom();
    expect(await u.room.init("g", { players: 2, seed: 77 } as Options, none, false, alice)).toEqual({ ok: true });
    expect(await u.room.adminSeed()).toMatchObject({ seed: 77, seeded: true });
    await u.room.join(bob);
    await u.room.startGame(alice);
    expect((await u.room.meta())?.options.seed).toBe(77);
  });

  it("is a random one when the host chose none (the administrator reads it all the same)", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    expect(await t.room.adminSeed()).toMatchObject({ seed: null, seeded: false });
    await t.room.join(bob);
    await t.room.startGame(alice);
    expect(await t.room.adminSeed()).toMatchObject({ seed: 4242, seeded: false });
  });
});

describe("the standing of a game in progress", () => {
  it("is part of the public data of a game that is being played: the round, the turn, the points (never the seed)", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    expect(await t.room.publicMeta()).not.toHaveProperty("progress");
    await t.room.join(bob);
    await t.room.startGame(alice);
    const pub = await t.room.publicMeta();
    expect(pub?.progress).toMatchObject({ actions: 0 });
    expect(pub?.progress?.scores).toHaveLength(2);
    expect(pub?.options).not.toHaveProperty("seed");
  });
});

describe("the seating of one seed", () => {
  it("gives the same players the same seats whoever made the table and in whatever order they joined", async () => {
    const seatsOf = async (host: Identity, other: Identity) => {
      const t = makeRoom({ seed: 4242 });
      await t.room.init("g", { players: 2 } as Options, none, false, host);
      await t.room.join(other);
      await t.room.startGame(host);
      return (await t.room.meta())?.seats.map((s) => s?.id);
    };
    expect(await seatsOf(alice, bob)).toEqual(await seatsOf(bob, alice));
  });
});

describe("the chat of a table", () => {
  type ChatMsg = Extract<ServerMessage, { t: "chat" }>;
  const chats = (c: Conn) => c.got.filter((m): m is ChatMsg => m.t === "chat");

  it("every connection gets each line, a player's with their seat and a spectator's without; a new connection gets the last lines", async () => {
    const t = makeRoom();
    const ca = new Conn("a", alice.id);
    const spec = new Conn("s", null);
    t.conns.push(ca, spec);
    await t.room.init("g", two, none, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice);
    expect(await t.room.chat(alice, "hello  there\n!")).toEqual({ ok: true });
    t.advance(1500);
    expect(await t.room.chat(cy, "from the stands")).toEqual({ ok: true }); // cy is not a player of the game
    for (const c of [ca, spec]) {
      const lines = chats(c).flatMap((m) => m.entries);
      expect(lines.map((l) => l.text)).toEqual(["hello there !", "from the stands"]);
      expect(lines[0]).toMatchObject({ n: 1, name: alice.name, seat: expect.any(Number) });
      expect(lines[1]).toMatchObject({ n: 2, seat: null });
    }
    const later = new Conn("l", null);
    t.conns.push(later);
    await t.room.connect(later);
    expect(chats(later)[0]).toMatchObject({ replace: true });
    expect(chats(later)[0]?.entries.map((l) => l.n)).toEqual([1, 2]);
  });

  it("refuses an empty line and a second line within a second, cuts a long line, and keeps the last 100", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    expect(await t.room.chat(alice, "   ")).toMatchObject({ ok: false, code: "empty" });
    expect(await t.room.chat(alice, "a")).toEqual({ ok: true });
    expect(await t.room.chat(alice, "b")).toMatchObject({ ok: false, code: "too_fast" });
    t.advance(1000);
    expect(await t.room.chat(alice, "x".repeat(1000))).toEqual({ ok: true });
    for (let i = 0; i < 105; i++) {
      t.advance(1000);
      await t.room.chat(bob, `line ${i}`);
    }
    const c = new Conn("c", null);
    t.conns.push(c);
    await t.room.connect(c);
    const lines = chats(c)[0]?.entries ?? [];
    expect(lines).toHaveLength(100);
    expect(lines.at(-1)?.text).toBe("line 104");
    expect(lines.at(0)?.n).toBe(lines.at(-1)?.n ? (lines.at(-1)?.n as number) - 99 : 0);
    expect((await t.store.get<{ text: string }[]>("chat"))?.every((l) => l.text.length <= 300)).toBe(true);
  });
});
