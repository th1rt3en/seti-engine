import type { Options } from "@seti/protocol";
import { describe, expect, it } from "vitest";
import { headerOf } from "../src/core/archive.js";
import { BOT_PLAYERS, BOT_RETRY_MS, toAct } from "../src/core/room.js";
import { FakeBot, alice, bob, makeRoom } from "./helpers.js";

const two = { players: 2 } as Options;
const three = { players: 3 } as Options;
const none = { kind: "none" } as const;

async function lobbyWithBot(rated = false, last = 6) {
  const bot = new FakeBot();
  const t = makeRoom({ bot, last });
  await t.room.init("g1", two, none, rated, alice);
  return { ...t, bot };
}

/** The human plays whenever it is their turn, and the AI answers in the background. */
async function playOut(t: Awaited<ReturnType<typeof lobbyWithBot>>): Promise<void> {
  for (let i = 0; i < 40; i++) {
    await t.room.botIdle();
    const meta = await t.room.meta();
    if (meta?.status !== "playing") return;
    const state = (await t.store.get("state")) as Parameters<typeof toAct>[0];
    const seat = meta.seats.findIndex((s) => s?.id === alice.id);
    if (toAct(state) === seat) await t.room.submit(alice, ((await t.store.get("logcount")) as number) ?? 0, { type: "score" });
  }
}

describe("an AI in the lobby", () => {
  it("only the host can add it, and only when they agree that the game is collected", async () => {
    const t = await lobbyWithBot();
    expect(await t.room.addBot(bob, "v001", true)).toMatchObject({ ok: false, code: "not_host" });
    expect(await t.room.addBot(alice, "v001", false)).toMatchObject({ ok: false, code: "consent" });
    expect((await t.room.meta())?.seats).toEqual([expect.objectContaining({ id: alice.id }), null]);
    expect(await t.room.addBot(alice, "v001", true)).toMatchObject({ ok: true });
  });

  it("is refused when there is no AI service, or the model name is odd", async () => {
    const t = makeRoom();
    await t.room.init("g1", two, none, false, alice);
    expect(await t.room.addBot(alice, "v001", true)).toMatchObject({ ok: false, code: "no_bot" });
    const u = await lobbyWithBot();
    expect(await u.room.addBot(alice, "../x", true)).toMatchObject({ ok: false, code: "bad_model" });
  });

  it("fills a seat, makes the game unrated, keeps the consent, and starts the game when it is the last seat", async () => {
    const t = await lobbyWithBot(true);
    const r = await t.room.addBot(alice, "v001", true);
    expect(r).toMatchObject({ ok: true });
    const meta = await t.room.meta();
    expect(meta?.rated).toBe(false);
    expect(meta?.consent).toMatchObject({ by: alice.id });
    expect(meta?.status).toBe("lobby"); // the lobby is full and waits for the host
    expect(await t.room.startGame(alice)).toEqual({ ok: true });
    const bots = (await t.room.meta())?.seats.filter((s) => s?.bot);
    expect(bots).toHaveLength(1);
    expect(bots?.[0]).toMatchObject({ name: "AI v001", registered: false, bot: { model: "v001" } });
    await t.room.botIdle();
  });

  it("is only for games of 2 players: a game of 1, 3 or 4 refuses it", async () => {
    expect(BOT_PLAYERS).toBe(2);
    for (const players of [1, 3, 4]) {
      const t = makeRoom({ bot: new FakeBot() });
      await t.room.init(`g${players}`, { players } as Options, none, false, alice);
      // a game of one player starts at once (there is no lobby to add anybody to); the others are lobbies
      expect(await t.room.addBot(alice, "v001", true)).toMatchObject({ ok: false, code: players === 1 ? "not_in_lobby" : "players" });
      const meta = await t.room.meta();
      expect(meta?.seats.some((s) => s?.bot)).toBe(false);
      expect(meta?.consent).toBeUndefined();
    }
  });

  it("the host can take it out again; the consent goes with the last AI (a lobby that holds one: adding it to a lobby of 2 starts the game)", async () => {
    const bot = new FakeBot();
    const t = makeRoom({ bot });
    await t.room.init("g1", three, none, false, alice);
    // the lobby is made as it would be if an AI had been put there: the room refuses to add one to a lobby of 3
    const before = (await t.room.meta()) as NonNullable<Awaited<ReturnType<typeof t.room.meta>>>;
    before.seats[1] = { id: "bot:v001:0", name: "AI v001", registered: false, bot: { model: "v001" } };
    before.consent = { by: alice.id, at: 1 };
    await t.store.put("meta", before);
    const seat = (await t.room.meta())?.seats.findIndex((s) => s?.bot) ?? -1;
    expect(seat).toBeGreaterThan(0);
    expect(await t.room.removeBot(bob, seat)).toMatchObject({ ok: false, code: "not_host" });
    expect(await t.room.removeBot(alice, 0)).toMatchObject({ ok: false, code: "not_bot" });
    expect(await t.room.removeBot(alice, seat)).toMatchObject({ ok: true });
    const meta = await t.room.meta();
    expect(meta?.seats[seat]).toBeNull();
    expect(meta?.consent).toBeUndefined();
  });
});

describe("an AI playing", () => {
  it("makes the moves of its seat, one request for each, with the whole log and the plan it gave last", async () => {
    const t = await lobbyWithBot(false, 6);
    await t.room.addBot(alice, "v001", true);
    await t.room.startGame(alice);
    await playOut(t);
    const meta = await t.room.meta();
    expect(meta?.status).toBe("finished");
    const log = await t.room.log();
    expect(log).toHaveLength(6);
    const botSeat = meta?.seats.findIndex((s) => s?.bot) ?? -1;
    expect(log.filter((e) => e.seat === botSeat)).toHaveLength(t.bot.requests.length);
    expect(t.bot.requests.every((r) => r.model === "v001" && r.seat === botSeat)).toBe(true);
    // the log it was given is the moves played so far; the plan it gave is passed back while the game is where it left it
    const second = t.bot.requests[1];
    const firstSeen = t.bot.requests[0];
    expect(second?.actions.length).toBeGreaterThan(firstSeen?.actions.length ?? 0);
    expect(firstSeen?.plan).toEqual([]);
  });

  it("does not hand the seed or any hidden state to anybody but the service (the public meta still hides the seed)", async () => {
    const t = await lobbyWithBot();
    await t.room.addBot(alice, "v001", true);
    await t.room.startGame(alice);
    expect((await t.room.publicMeta())?.options.seed).toBeUndefined();
    await playOut(t);
    expect(t.bot.requests[0]?.options.seed).toBe(4242);
  });

  it("a service that fails is asked again when the alarm rings, and the game goes on", async () => {
    const t = await lobbyWithBot();
    t.bot.failing = true;
    await t.room.addBot(alice, "v001", true);
    await t.room.startGame(alice);
    await playOut(t);
    expect((await t.room.log()).length).toBeLessThan(6);
    expect(t.alarms.at(-1)).toBe(t.clock() + BOT_RETRY_MS);
    t.bot.failing = false;
    t.advance(BOT_RETRY_MS);
    await t.room.onAlarm();
    await playOut(t);
    expect((await t.room.meta())?.status).toBe("finished");
  });

  it("a game with an AI is never rated, even if the record of its start or its end says so", async () => {
    const t = await lobbyWithBot(true);
    await t.room.addBot(alice, "v001", true);
    // the host's lobby was rated when it was made; the AI took the flag away, and the start does not give it back
    await t.room.startGame(alice);
    expect(t.sink.starts.at(-1)?.rated).toBe(false);
    expect(t.sink.lobbies.at(-1)?.rated).toBe(false);
  });

  it("a game with an AI is not rated, and the archive says which seat was the model and that the host agreed", async () => {
    const t = await lobbyWithBot(true);
    await t.room.addBot(alice, "v001", true);
    await t.room.startGame(alice);
    await playOut(t);
    expect(t.sink.ends).toHaveLength(1);
    expect(t.sink.ends[0]?.rec.rated).toBe(false);
    const meta = (await t.room.meta()) as NonNullable<Awaited<ReturnType<typeof t.room.meta>>>;
    const header = headerOf(meta);
    expect(header.consent).toMatchObject({ by: alice.id });
    expect(header.seats.filter((s) => s.bot)).toEqual([
      expect.objectContaining({ bot: { model: "v001" }, userId: expect.stringMatching(/^bot:v001:/) }),
    ]);
    expect(header.seats.find((s) => s.userId === alice.id)?.bot).toBeUndefined();
  });

  it("a game without an AI has no consent in its header", async () => {
    const t = makeRoom();
    await t.room.init("g1", two, none, false, alice);
    await t.room.join(bob);
    const header = headerOf((await t.room.meta()) as never);
    expect(header.consent).toBeUndefined();
    expect(header.seats.every((s) => s.bot === undefined)).toBe(true);
  });
});
