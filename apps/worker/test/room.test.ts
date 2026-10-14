import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import type { ServerMessage } from "../src/core/room.js";
import { Conn, alice, bob, cy, guest, makeRoom } from "./helpers.js";

const two = { players: 2 } as Options;
const none = { kind: "none" } as const;

async function started(rated = false, last = 6) {
  const t = makeRoom({ last });
  await t.room.init("g1", two, none, rated, alice);
  await t.room.join(bob);
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
    await t.room.join(cy);
    await t.room.leave(alice);
    expect((await t.room.meta())?.host).toBe(bob.id);
    await t.room.leave(bob);
    expect((await t.room.meta())?.host).toBe(cy.id);
    // a player who rejoins goes to the back of the line
    await t.room.join(alice);
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

  it("refuses: not your turn, a stale count, an illegal action, a stranger", async () => {
    const t = await started();
    expect(await t.room.submit(bob, 0, { type: "score" })).toMatchObject({ ok: false, code: "not_your_turn" });
    expect(await t.room.submit(alice, 5, { type: "score" })).toMatchObject({ ok: false, code: "stale" });
    expect(await t.room.submit(alice, 0, { type: "launch" })).toMatchObject({ ok: false, code: "illegal", legal: [{ type: "score" }] });
    expect(await t.room.submit(cy, 0, { type: "score" })).toMatchObject({ ok: false, code: "not_seated" });
    expect(await t.room.log()).toHaveLength(0);
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
    await t.room.leave(bob);
    expect(t.sink.lobbies.map((m) => m.seats.filter((s) => s !== null).length)).toEqual([1, 2, 1]);
  });
});

describe("a failing engine", () => {
  it("gives the seat back when the game cannot be started", async () => {
    const t = makeRoom();
    await t.room.init("g", two, none, false, alice);
    const engine = (t as unknown as { room: { d: { engine: { newGame: () => Promise<never> } } } }).room.d.engine;
    const good = engine.newGame;
    engine.newGame = async () => {
      throw new Error("engine down");
    };
    await expect(t.room.join(bob)).rejects.toThrow("engine down");
    expect((await t.room.meta())?.seats[1]).toBeNull();
    expect((await t.room.meta())?.status).toBe("lobby");
    engine.newGame = good;
    expect(await t.room.join(bob)).toMatchObject({ ok: true, seat: 1 });
    expect((await t.room.meta())?.status).toBe("playing");
  });
});
