// The simultaneous setup of the organization module (EXP-ORG-14, owner 2026-10-23): every player chooses at the same time and locks in; the clocks run for
// all of them; nobody sees a choice before everybody has locked in. The engine is a small double that has the same shape (the decisions of all seats open at
// once, the moves naming their seat); the real engine is played through the room in integration.test.ts.
import type { GameState, Options, StepResult, View } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { type Action, type Engine, IllegalAction } from "../src/core/engine.js";
import { publicEntry } from "../src/core/publicLog.js";
import { type BotClient, type BotReply, type BotRequest, type ServerMessage, actors } from "../src/core/room.js";
import { Conn, alice, bob, makeRoom } from "./helpers.js";

interface Sim {
  phase: "setup" | "play" | "finished";
  pending: { kind: string; player: number }[];
  players: { index: number; score: number; setup_org: string | null; setup_locked: boolean }[];
  current_player: number;
  final_scores: unknown[];
  winners: number[];
  rival: null;
  played: number;
}

/** Players choose an organization (`choose_org`, any number of times) and then `setup_lock`; when all have locked in the game is played with `score`. */
class SimulEngine implements Engine {
  private state(players: number): Sim {
    return {
      phase: "setup",
      pending: Array.from({ length: players }, (_, player) => ({ kind: "setup_choice", player })),
      players: Array.from({ length: players }, (_, index) => ({ index, score: 0, setup_org: null, setup_locked: false })),
      current_player: 0,
      final_scores: [],
      winners: [],
      rival: null,
      played: 0,
    };
  }
  private legal(s: Sim): Action[] {
    if (s.phase === "setup")
      return s.pending.flatMap((d) => {
        const p = s.players[d.player] as Sim["players"][number];
        return [
          { type: "choose_org", org: "a", seat: d.player },
          { type: "choose_org", org: "b", seat: d.player },
          ...(p.setup_org ? [{ type: "setup_lock", seat: d.player }] : []),
        ];
      });
    return s.phase === "play" ? [{ type: "score" }] : [];
  }
  async newGame(options: Options): Promise<StepResult> {
    const state = this.state(options.players);
    (state as unknown as { options: Options }).options = options;
    return { state, events: [], legal: this.legal(state) } as unknown as StepResult;
  }
  async apply(state: GameState, action: Action): Promise<StepResult> {
    const s = structuredClone(state) as unknown as Sim;
    if (!this.legal(s).some((m) => JSON.stringify(m) === JSON.stringify(action))) throw new IllegalAction("not legal", this.legal(s));
    const events: Record<string, unknown>[] = [];
    if (s.phase === "setup") {
      const p = s.players[action.seat as number] as Sim["players"][number];
      if (action.type === "choose_org") p.setup_org = action.org as string;
      else {
        p.setup_locked = true;
        s.pending = s.pending.filter((d) => d.player !== action.seat);
        events.push({ type: "setup_locked", player: action.seat });
        if (s.pending.length === 0) {
          s.phase = "play";
          for (const q of s.players) events.push({ type: "organization", player: q.index, org: q.setup_org });
        }
      }
    } else {
      s.played++;
      s.players[s.current_player] = {
        ...(s.players[s.current_player] as Sim["players"][number]),
        score: (s.players[s.current_player] as Sim["players"][number]).score + 1,
      };
      s.current_player = (s.current_player + 1) % s.players.length;
      if (s.played >= 4) {
        s.phase = "finished";
        s.final_scores = s.players.map((q) => ({ player: q.index, total: q.score }));
        s.winners = [0];
      }
    }
    return { state: s, events, legal: this.legal(s) } as unknown as StepResult;
  }
  async project(state: GameState, viewer: number | null): Promise<View> {
    const s = state as unknown as Sim;
    const mine = this.legal(s).filter((m) => s.phase !== "setup" || m.seat === viewer);
    return { viewer, state, counts: {}, to_act: viewer, acting: actors(state), legal: viewer === null ? [] : mine } as unknown as View;
  }
}

/** The AI: chooses an organization, then locks in, whatever the person has done. */
class SimBot implements BotClient {
  requests: BotRequest[] = [];
  async move(req: BotRequest): Promise<BotReply> {
    this.requests.push(structuredClone(req));
    const mine = req.actions.filter((a) => a.seat === req.seat);
    if (mine.length === 0) return { action: { type: "choose_org", org: "b", seat: req.seat }, plan: [] };
    if (mine.length === 1) return { action: { type: "setup_lock", seat: req.seat }, plan: [] };
    return { action: { type: "score" }, plan: [] };
  }
}

const withOrgs = { players: 2, organizations: true, expansion: true } as Options;
const none = { kind: "none" } as const;
const bank = { kind: "bank", initialMs: 10_000, incrementMs: 1000 } as const;

async function game(options: Options = withOrgs, clock: Parameters<ReturnType<typeof makeRoom>["room"]["init"]>[2] = none) {
  const t = makeRoom({ engine: new SimulEngine() });
  const ca = new Conn("a", alice.id);
  const cb = new Conn("b", bob.id);
  const spec = new Conn("s", null);
  t.conns.push(ca, cb, spec);
  await t.room.init("g1", options, clock, false, alice);
  await t.room.join(bob);
  const meta = await t.room.meta();
  const seatOf = (who: typeof alice) => (meta?.seats ?? []).findIndex((s) => s?.id === who.id);
  return { ...t, ca, cb, spec, a: seatOf(alice), b: seatOf(bob) };
}

const count = async (t: Awaited<ReturnType<typeof game>>) => ((await t.store.get("logcount")) as number | undefined) ?? 0;

describe("the simultaneous setup", () => {
  it("is switched on for a game with organizations and 2 or more players, and only for those", async () => {
    expect((await (await game()).room.meta())?.options).toMatchObject({ simul_setup: true });
    const solo = makeRoom({ engine: new SimulEngine() });
    await solo.room.init("g2", { players: 1, organizations: true, expansion: true } as Options, none, false, alice);
    expect((await solo.room.meta())?.options.simul_setup).toBeUndefined();
    const plain = makeRoom({ engine: new SimulEngine() });
    await plain.room.init("g3", { players: 2 } as Options, none, false, alice);
    await plain.room.join(bob);
    expect((await plain.room.meta())?.options.simul_setup).toBeUndefined();
  });

  it("asks every seat who has not locked in, in any order, and each seat moves on its own", async () => {
    const t = await game();
    expect(actors((await t.store.get("state")) as GameState).sort()).toEqual([0, 1]);
    // bob is second in the list, but moves first; alice moves after (the engine would refuse this when the turns were one after another)
    expect(await t.room.submit(bob, 0, { type: "choose_org", org: "a", seat: t.b })).toEqual({ ok: true });
    expect(await t.room.submit(alice, 1, { type: "choose_org", org: "b", seat: t.a })).toEqual({ ok: true });
    expect(await t.room.submit(bob, 2, { type: "setup_lock", seat: t.b })).toEqual({ ok: true });
    expect(actors((await t.store.get("state")) as GameState)).toEqual([t.a]);
    expect(await t.room.submit(bob, 3, { type: "choose_org", org: "a", seat: t.b })).toMatchObject({ ok: false, code: "not_your_turn" }); // locked in
    expect(await t.room.submit(alice, 3, { type: "setup_lock", seat: t.a })).toEqual({ ok: true });
    expect(((await t.store.get("state")) as GameState).phase).toBe("play");
  });

  it("does not let a player move for another seat", async () => {
    const t = await game();
    const res = await t.room.submit(alice, 0, { type: "choose_org", org: "a", seat: t.b });
    expect(res).toMatchObject({ ok: false, code: "not_your_turn" });
    expect(await count(t)).toBe(0);
  });

  it("shows nothing of a choice to the others: not in the log and not in the view", async () => {
    const t = await game();
    await t.room.submit(alice, 0, { type: "choose_org", org: "b", seat: t.a });
    const logs = (c: Conn) => c.got.filter((m): m is Extract<ServerMessage, { t: "log" }> => m.t === "log").flatMap((m) => m.entries);
    expect(logs(t.ca).at(-1)?.action).toMatchObject({ type: "choose_org", org: "b" }); // its own choice
    expect(logs(t.cb).at(-1)?.action).toEqual({ type: "choose_org", seat: t.a }); // the others do not see which
    expect(logs(t.spec).at(-1)?.action).toEqual({ type: "choose_org", seat: t.a });
    const entry = (await t.room.log())[0];
    expect(entry && publicEntry(entry, t.b).action).not.toHaveProperty("org");
    expect(entry && publicEntry(entry, t.a).action).toHaveProperty("org", "b");
  });

  it("runs the clock of every player who has not locked in, and stops each one when it locks in", async () => {
    const t = await game(withOrgs, bank);
    t.advance(3000);
    const view = () => (t.ca.last("view") as Extract<ServerMessage, { t: "view" }>).remaining;
    await t.room.submit(alice, 0, { type: "choose_org", org: "a", seat: t.a });
    await t.room.submit(alice, 1, { type: "setup_lock", seat: t.a });
    // alice used 3 s and got the increment; bob's clock is still running from the start
    expect(view()?.[t.a]).toBe(10_000 - 3000 + 1000);
    t.advance(2000);
    await t.room.submit(bob, 2, { type: "choose_org", org: "a", seat: t.b });
    await t.room.submit(bob, 3, { type: "setup_lock", seat: t.b });
    expect((t.cb.last("view") as Extract<ServerMessage, { t: "view" }>).remaining?.[t.b]).toBe(10_000 - 5000 + 1000); // 5 s since the start
    // and the clock goes to the player to act in the game
    const clock = (await t.store.get("clock")) as { runs: { seat: number }[] };
    expect(clock.runs).toHaveLength(1);
  });

  it("ends the game for the player whose time runs out first while they are choosing (a game of 2)", async () => {
    const t = await game(withOrgs, bank);
    await t.room.submit(alice, 0, { type: "choose_org", org: "a", seat: t.a });
    await t.room.submit(alice, 1, { type: "setup_lock", seat: t.a });
    t.advance(11_000); // bob never locked in: his 10 s are over
    await t.room.onAlarm();
    const meta = await t.room.meta();
    expect(meta?.status).toBe("finished");
    expect(meta?.result).toMatchObject({ reason: "timeout", forfeit: t.b });
  });

  it("asks the AI for its seat at once, and the AI locks in without waiting for the person", async () => {
    const bot = new SimBot();
    const t = makeRoom({ engine: new SimulEngine(), bot });
    const ca = new Conn("a", alice.id);
    t.conns.push(ca);
    await t.room.init("g1", withOrgs, none, false, alice);
    await t.room.addBot(alice, "v001", true);
    await t.room.botIdle();
    const state = (await t.store.get("state")) as GameState;
    const meta = await t.room.meta();
    const botSeat = meta?.seats.findIndex((s) => s?.bot) as number;
    expect(state.phase).toBe("setup");
    expect(actors(state)).toEqual([1 - botSeat]); // only the person is still choosing
    expect(bot.requests.map((r) => r.seat)).toEqual([botSeat, botSeat]); // its two moves: the organization, the lock
    const me = botSeat === 0 ? 1 : 0;
    await t.room.submit(alice, 2, { type: "choose_org", org: "a", seat: me });
    await t.room.submit(alice, 3, { type: "setup_lock", seat: me });
    await t.room.botIdle();
    expect(((await t.store.get("state")) as GameState).phase).not.toBe("setup");
  });

  it("takes a move of the setup whatever count of actions the client had seen (the others move at the same time)", async () => {
    const t = await game();
    expect(await t.room.submit(bob, 0, { type: "choose_org", org: "a", seat: t.b })).toEqual({ ok: true });
    expect(await t.room.submit(alice, 0, { type: "choose_org", org: "b", seat: t.a })).toEqual({ ok: true }); // alice saw 0 actions, there is 1
    expect(await count(t)).toBe(2);
  });
});
