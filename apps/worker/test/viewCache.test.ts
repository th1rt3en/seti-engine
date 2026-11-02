import type { GameState, Options, StepResult, View } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import type { Action } from "../src/core/engine.js";
import { Conn, FakeEngine, alice, bob, makeRoom } from "./helpers.js";

// The views that the players are sent after a move come with the move from the engine (one round trip), and a view is worked out once for each state.

class CountingEngine extends FakeEngine {
  applied = 0;
  withViews: (number | null)[][] = [];
  projected: (number | null)[] = [];
  override async apply(state: GameState, action: Action): Promise<StepResult> {
    this.applied++;
    return super.apply(state, action);
  }
  async applyWithViews(state: GameState, action: Action, viewers: (number | null)[]) {
    this.withViews.push(viewers);
    const result = await super.apply(state, action);
    return { result, views: await Promise.all(viewers.map((v) => super.project(result.state, v))) };
  }
  override async project(state: GameState, viewer: number | null): Promise<View> {
    this.projected.push(viewer);
    return super.project(state, viewer);
  }
}

async function table() {
  const engine = new CountingEngine(20);
  const t = makeRoom({ engine });
  await t.room.init("g1", { players: 2 } as Options, { kind: "none" }, false, alice);
  await t.room.join(bob);
  await t.room.startGame(alice);
  const tabs = [new Conn("a1", alice.id), new Conn("a2", alice.id), new Conn("b1", bob.id), new Conn("s1", null)];
  for (const c of tabs) {
    t.conns.push(c);
    await t.room.connect(c);
  }
  engine.projected.length = 0;
  return { ...t, engine, tabs };
}

const viewOf = (c: Conn) => c.last("view") as unknown as { seq: number; view: { viewer: number | null; state: { played: number } } };

describe("the views after a move", () => {
  it("come with the move, one for each seat that is connected, whatever the number of connections", async () => {
    const t = await table();
    expect(await t.room.submit(alice, 0, { type: "score" })).toEqual({ ok: true });
    expect(t.engine.applied).toBe(0);
    expect(t.engine.withViews).toEqual([[0, 1, null]]); // two tabs of Alice are one seat
    expect(t.engine.projected).toEqual([]); // nothing is asked of the engine again
    for (const [c, viewer] of [
      [t.tabs[0], 0],
      [t.tabs[1], 0],
      [t.tabs[2], 1],
      [t.tabs[3], null],
    ] as const) {
      const v = viewOf(c as Conn);
      expect(v.seq).toBe(1);
      expect(v.view.viewer).toBe(viewer);
      expect(v.view.state.played).toBe(1);
    }
  });

  it("a connection that comes later gets its view worked out once, and a second one of the same seat shares it", async () => {
    const t = await table();
    await t.room.submit(alice, 0, { type: "score" });
    const late = [new Conn("late1", bob.id), new Conn("late2", bob.id)];
    for (const c of late) {
      t.conns.push(c);
      await t.room.connect(c);
    }
    expect(viewOf(late[0] as Conn).view.viewer).toBe(1);
    expect(viewOf(late[1] as Conn).view.state.played).toBe(1);
    expect(t.engine.projected).toEqual([]); // Bob's view of this state came with the move
    const carol = new Conn("late3", null);
    const dan = new Conn("late4", null);
    t.conns.push(carol, dan);
    await Promise.all([t.room.connect(carol), t.room.connect(dan)]);
    expect(t.engine.projected.length).toBeLessThanOrEqual(1); // the spectator view came with the move too
  });

  it("are not kept for the next state", async () => {
    const t = await table();
    await t.room.submit(alice, 0, { type: "score" });
    await t.room.submit(bob, 1, { type: "score" });
    expect(viewOf(t.tabs[0] as Conn).seq).toBe(2);
    expect(viewOf(t.tabs[0] as Conn).view.state.played).toBe(2);
    expect(t.engine.withViews).toHaveLength(2);
  });

  it("an illegal move is refused with the legal moves, and nothing changes", async () => {
    const t = await table();
    const res = await t.room.submit(alice, 0, { type: "nonsense" });
    expect(res).toMatchObject({ ok: false, code: "illegal" });
    expect(viewOf(t.tabs[0] as Conn).seq).toBe(0);
  });

  it("without connections nothing is asked for", async () => {
    const engine = new CountingEngine(20);
    const t = makeRoom({ engine });
    await t.room.init("g1", { players: 2 } as Options, { kind: "none" }, false, alice);
    await t.room.join(bob);
    await t.room.startGame(alice);
    await t.room.submit(alice, 0, { type: "score" });
    expect(engine.applied).toBe(1);
    expect(engine.withViews).toEqual([]);
  });
});
