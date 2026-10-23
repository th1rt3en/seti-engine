// Plays whole games through the game room against the real engine service.
// Run it with the service up:  SETI_ENGINE_URL=http://127.0.0.1:8080 pnpm --filter @seti/worker test   (skipped otherwise)
import type { GameState, Options, View } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { HttpEngine } from "../src/core/engine.js";
import { EngineArchive } from "../src/core/engineArchive.js";
import { makeSigner } from "../src/core/engineAuth.js";
import { type Deps, GameRoom, type ServerMessage } from "../src/core/room.js";
import { Conn, MemoryStore, RecordingSink, alice, bob, cy } from "./helpers.js";

const url = process.env.SETI_ENGINE_URL;

async function play(options: Options, ids = [alice, bob]) {
  const store = new MemoryStore();
  const sink = new RecordingSink();
  const conns: Conn[] = ids.map((who, i) => new Conn(`c${i}`, who.id));
  const spectator = new Conn("spec", null);
  const signKey = process.env.SETI_ENGINE_SIGNING_KEY;
  const sign = signKey ? makeSigner(signKey, "worker") : undefined;
  const engine = new HttpEngine(url as string, undefined, sign);
  let t = 1_000_000;
  const deps: Deps = {
    store,
    engine,
    sink,
    archive: new EngineArchive(url as string, undefined, sign),
    now: () => t++,
    newSeed: () => 20260513,
    connections: () => [...conns, spectator],
    setAlarm: async () => {},
  };
  const room = new GameRoom(deps);
  await room.init("g", options, { kind: "none" }, false, ids[0] as typeof alice);
  for (const who of ids.slice(1)) await room.join(who);
  let n = 0;
  let seed = 7;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed;
  };
  while ((await room.meta())?.status === "playing") {
    const seats = conns.map((c) => c.last("view") as Extract<ServerMessage, { t: "view" }>);
    const view = seats.find((v) => (v.view as View).legal.length > 0);
    expect(view, "someone must be able to act").toBeDefined();
    const v = view as Extract<ServerMessage, { t: "view" }>;
    const actor = v.view.to_act as number;
    const legal = v.view.legal;
    const move = legal[rnd() % legal.length] as Record<string, unknown>;
    const mover = (await room.meta())?.seats[actor] as typeof alice;
    const res = await room.submit(mover, v.seq, move);
    expect(res).toEqual({ ok: true });
    n++;
    expect(n).toBeLessThan(5000);
  }
  await room.archived();
  return { room, store, sink, conns, spectator, engine, actions: n };
}

describe.skipIf(!url)("a game through the room and the real engine", () => {
  it("a 2-player game runs to the end, is recorded and can be replayed from its seed and log", async () => {
    const g = await play({ players: 2 } as Options);
    const meta = await g.room.meta();
    expect(meta?.status).toBe("finished");
    expect(g.sink.ends).toHaveLength(1);
    const end = g.sink.ends[0];
    expect(end?.rec.result.reason).toBe("completed");
    expect(end?.rec.result.ranking).toHaveLength(2);
    // D8: the seed and the log reproduce the game
    let r = await g.engine.newGame(meta?.options as Options);
    for (const e of await g.room.log()) r = await g.engine.apply(r.state, e.action);
    const final = await g.store.get<GameState>("state");
    expect(r.state).toEqual(final);
    expect(r.state.phase).toBe("finished");
    // the random state is a string, so JavaScript keeps it whole between two moves; the engine's own replay (the one that makes the statistics)
    // must then reproduce the game exactly: it throws when an action is not legal in its replay
    expect(typeof final?.rng_state).toBe("string");
    const stats = await g.engine.stats?.(
      meta?.options as Options,
      (await g.room.log()).map((e) => e.action),
      "exact",
    );
    expect(stats?.players).toHaveLength(2);
  }, 120_000);

  it("the views never show the other player's hand or the deck", async () => {
    const g = await play({ players: 2 } as Options);
    for (const c of g.conns) {
      const v = (c.last("view") as Extract<ServerMessage, { t: "view" }>).view as View;
      expect(v.viewer).toBe((await g.room.meta())?.seats.findIndex((x) => x?.id === c.who)); // the view is the one of this connection's seat
      const other = v.state.players[1 - (v.viewer as number)];
      expect(other?.hand.every((x) => x === "?")).toBe(true);
      expect(v.state.deck.every((x) => x === "?")).toBe(true);
      expect(v.state.rng_state).toBe("0");
    }
  }, 120_000);

  it("a game with organizations: both players choose at the same time, in secret, and the game goes on to the end (EXP-ORG-14)", async () => {
    const g = await play({ players: 2, expansion: true, organizations: true } as Options);
    expect((await g.room.meta())?.status).toBe("finished");
    const meta = await g.room.meta();
    expect(meta?.options.simul_setup).toBe(true);
    const log = await g.room.log();
    const locks = log.filter((e) => e.action.type === "setup_lock");
    expect(locks).toHaveLength(2);
    // both choices were made before the first lock, in any seat order, and each move names its own seat
    const firstLock = log.findIndex((e) => e.action.type === "setup_lock");
    expect(log.slice(0, firstLock).every((e) => e.action.seat === e.seat)).toBe(true);
    // the replay of the log reproduces the game
    let r = await g.engine.newGame(meta?.options as Options);
    for (const e of log) r = await g.engine.apply(r.state, e.action);
    expect(r.state).toEqual(await g.store.get<GameState>("state"));
    expect(g.sink.ends[0]?.rec.result.reason).toBe("completed");
  }, 180_000);

  it("a solo game against the rival runs to the end", async () => {
    const g = await play({ players: 1, difficulty: 3 } as Options, [alice]);
    expect((await g.room.meta())?.status).toBe("finished");
    const result = g.sink.ends[0]?.rec.result;
    expect(result?.winners.length).toBeLessThanOrEqual(1);
    expect(g.sink.ends[0]?.rec.rated).toBe(false);
  }, 120_000);
});

describe.skipIf(!url)("simultaneous games", () => {
  it("12 games played at the same time all finish, each with its own log", async () => {
    const started = Date.now();
    const games = await Promise.all(
      Array.from({ length: 12 }, (_, i) =>
        play({ players: i % 2 === 0 ? 2 : 3 } as Options, i % 2 === 0 ? [alice, bob] : [alice, bob, cy]),
      ),
    );
    for (const g of games) {
      expect((await g.room.meta())?.status).toBe("finished");
      expect(g.sink.ends[0]?.rec.result.reason).toBe("completed");
      expect((await g.room.log()).length).toBe(g.actions);
    }
    console.log(`12 games, ${games.reduce((a, g) => a + g.actions, 0)} actions in ${Date.now() - started} ms`);
  }, 600_000);
});
