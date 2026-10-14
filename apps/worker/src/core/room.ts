// The game room: one game's lifecycle (lobby, play, end), its clock, its action log and what each player may see.
// It holds no rules (CLAUDE.md rule 5): every move goes to the engine service, and every view comes from the engine's projection.
// The Durable Object (gameRoom.ts) is a thin adapter around this class; everything here is testable without Cloudflare.
import type { GameState, Options, View } from "@seti/protocol";
import { type Archive, type ReplayFile, actionPath, headerOf, headerPath, replayOf, replayPath, resultPath } from "./archive.js";
import type { Identity } from "./auth.js";
import * as clocks from "./clock.js";
import type { Action, Engine } from "./engine.js";
import { IllegalAction } from "./engine.js";
import { type PublicEntry, publicEntry } from "./publicLog.js";
import { shuffledSeats } from "./seating.js";

export type Status = "lobby" | "playing" | "finished" | "cancelled";
export type EndReason = "completed" | "resigned" | "timeout" | "kicked";

/** Games of this many players or more are not ended by a clock: a player whose clock is negative can be kicked (decision D24). */
export const KICK_FROM_PLAYERS = 3;

export interface Meta {
  id: string;
  status: Status;
  options: Options;
  clock: clocks.ClockSettings;
  rated: boolean;
  seats: (Identity | null)[];
  /** The id of the host: the player who created the lobby, or the player who has been in it the longest after the host left (decision D27). */
  host: string;
  /** The ids of the players in the lobby, in the order they joined. */
  joined: string[];
  createdAt: number;
  startedAt?: number;
  endedAt?: number;
  result?: Result;
}

export interface LogEntry {
  seq: number;
  seat: number;
  action: Action;
  at: number;
  /** What the engine reported for this action (the replay shows them). */
  events: Record<string, unknown>[];
}

export interface RankedSeat {
  seat: number;
  /** 1 is the best; equal ranks are a tie. */
  rank: number;
  score: number;
}

export interface Result {
  reason: EndReason;
  /** The seat that resigned or timed out. */
  forfeit?: number;
  ranking: RankedSeat[];
  winners: number[];
  /** The engine's final score rows (completed games only). */
  finalScores: unknown[];
}

export interface GameRecord {
  meta: Meta;
  result: Result;
  actions: number;
  /** True when the result counts for the ratings. */
  rated: boolean;
}

export interface Store {
  get<T>(key: string): Promise<T | undefined>;
  put(key: string, value: unknown): Promise<void>;
  /** Values of the keys with this prefix, in key order. */
  list<T>(prefix: string): Promise<T[]>;
  /** Delete everything the game stored. */
  clear(): Promise<void>;
}

export interface ResultSink {
  /** The game exists (it is in its lobby) or its seats changed: the lobby page lists such games. */
  recordLobby(meta: Meta): Promise<void>;
  /** The lobby was emptied and destroyed: forget it. */
  removeLobby(id: string): Promise<void>;
  recordStart(meta: Meta): Promise<void>;
  recordEnd(rec: GameRecord, log: LogEntry[]): Promise<void>;
}

export interface Deps {
  store: Store;
  engine: Engine;
  sink: ResultSink;
  /** Where every game is logged for replays (decision D25). */
  archive: Archive;
  now(): number;
  newSeed(): number;
  /** The open connections (a hibernating Durable Object rebuilds them from its sockets). */
  connections(): Connection[];
  /** Ask for `onAlarm` to be called at that time (null cancels). */
  setAlarm(at: number | null): Promise<void>;
  /** Keep the object alive until this work is done (the Durable Object passes it to `waitUntil`). */
  defer?(work: Promise<unknown>): void;
}

export type ServerMessage =
  | { t: "lobby"; status: Status; seats: ({ name: string } | null)[]; host: string | null; rated: boolean; clock: clocks.ClockSettings }
  | { t: "view"; seq: number; status: Status; view: View; names: string[]; remaining: (number | null)[] | null }
  | { t: "error"; code: string; message: string; legal?: Action[] }
  /** The moves made so far, for the log beside the board: all of them on connecting (`from` is 0), then each new one. */
  | { t: "log"; from: number; entries: PublicEntry[] }
  | { t: "ended"; result: Result };

export interface Connection {
  id: string;
  /** The id of the player on this connection, or null for a spectator. Its seat is looked up when a view is sent, because the seats are drawn when the game starts. */
  who: string | null;
  send(msg: ServerMessage): void;
}

export type SubmitResult = { ok: true } | { ok: false; code: string; message: string; legal?: Action[] };

const logKey = (seq: number): string => `log:${String(seq).padStart(7, "0")}`;

/** The player the engine waits for (the same rule as the engine's `to_act`). */
export function toAct(state: GameState): number | null {
  if (state.phase === "finished") return null;
  const first = state.pending[0];
  if (first) return first.player;
  return state.phase === "play" ? state.current_player : null;
}

interface ArchiveProgress {
  header: boolean;
  actions: number;
  done: boolean;
}

const ARCHIVE_RETRY_MS = 60_000;

/** A client in a lobby sends a ping every LOBBY_PING_MS; a player not heard from for LOBBY_GRACE_MS has left (decision D27). */
export const LOBBY_PING_MS = 15_000;
export const LOBBY_GRACE_MS = 60_000;
const LOBBY_CHECK_MS = 20_000;

export class GameRoom {
  constructor(private readonly d: Deps) {}

  // Every change of a game runs one at a time: the engine call lets other messages in, and two moves must not both pass the same check.
  private queue: Promise<unknown> = Promise.resolve();
  private archiveQueue: Promise<unknown> = Promise.resolve();

  private serial<T>(work: () => Promise<T>): Promise<T> {
    const run = this.queue.then(work, work);
    this.queue = run.catch(() => undefined);
    return run;
  }

  // --- lobby ---------------------------------------------------------------------------------------------------------------

  async init(id: string, options: Options, clock: clocks.ClockSettings, rated: boolean, host: Identity): Promise<SubmitResult> {
    if ((await this.d.store.get<Meta>("meta")) !== undefined) return fail("exists", "the game already exists");
    if (rated && (options.players < 2 || options.players > 4)) return fail("not_rateable", "rated games have 2 to 4 players");
    if (rated && !host.registered) return fail("guest", "only registered players can play rated games");
    const seats: (Identity | null)[] = Array(options.players).fill(null);
    seats[0] = host;
    const meta: Meta = { id, status: "lobby", options, clock, rated, seats, host: host.id, joined: [host.id], createdAt: this.d.now() };
    await this.d.store.put("meta", meta);
    await this.d.sink.recordLobby(meta);
    if (options.players === 1) await this.start(meta);
    else {
      await this.markSeen(host.id);
      await this.broadcastLobby(meta);
      await this.d.setAlarm(this.d.now() + LOBBY_CHECK_MS);
    }
    return { ok: true };
  }

  join(who: Identity): Promise<SubmitResult & { seat?: number }> {
    return this.serial(() => this.doJoin(who));
  }

  private async doJoin(who: Identity): Promise<SubmitResult & { seat?: number }> {
    const meta = await this.meta();
    if (meta === undefined) return fail("unknown_game", "no such game");
    const seat = meta.seats.findIndex((s) => s?.id === who.id);
    if (seat >= 0) return { ok: true, seat };
    if (meta.status !== "lobby") return fail("started", "the game has already started");
    if (meta.rated && !who.registered) return fail("guest", "only registered players can play rated games");
    const free = meta.seats.findIndex((s) => s === null);
    if (free < 0) return fail("full", "the game is full");
    meta.seats[free] = who;
    meta.joined.push(who.id);
    await this.markSeen(who.id);
    await this.d.store.put("meta", meta);
    await this.d.sink.recordLobby(meta);
    const lobbySeats = [...meta.seats];
    if (meta.seats.every((s) => s !== null)) {
      try {
        await this.start(meta);
      } catch (e) {
        // the engine could not start the game: give the seat back so that the player can try again
        meta.status = "lobby";
        meta.seats = lobbySeats;
        (meta.seats as (Identity | null)[])[free] = null;
        meta.joined = meta.joined.filter((id) => id !== who.id);
        await this.d.store.put("meta", meta);
        await this.d.sink.recordLobby(meta);
        throw e;
      }
    } else await this.broadcastLobby(meta);
    return { ok: true, seat: free };
  }

  leave(who: Identity): Promise<SubmitResult> {
    return this.serial(() => this.doLeave(who));
  }

  private async doLeave(who: Identity): Promise<SubmitResult> {
    const meta = await this.meta();
    if (meta === undefined || meta.status !== "lobby") return fail("not_in_lobby", "the game is not in its lobby");
    if (!meta.seats.some((s) => s?.id === who.id)) return fail("not_seated", "you are not in this game");
    await this.removeFromLobby(meta, who.id);
    return { ok: true };
  }

  /** A player leaves the lobby, or is taken to have left because they stopped answering pings. */
  private async removeFromLobby(meta: Meta, id: string): Promise<boolean> {
    const seat = meta.seats.findIndex((s) => s?.id === id);
    if (seat >= 0) meta.seats[seat] = null;
    meta.joined = meta.joined.filter((j) => j !== id);
    const seen = (await this.d.store.get<Record<string, number>>("seen")) ?? {};
    delete seen[id];
    if (meta.joined.length === 0) {
      // Nobody is left: the lobby is destroyed (decision D27), and a link to it leads nowhere.
      meta.status = "cancelled";
      await this.broadcastLobby(meta);
      await this.d.sink.removeLobby(meta.id);
      await this.d.store.clear();
      await this.d.setAlarm(null);
      return true;
    }
    // The host left: the player who joined next is the host now.
    if (meta.host === id) meta.host = meta.joined[0] as string;
    await this.d.store.put("meta", meta);
    await this.d.store.put("seen", seen);
    await this.d.sink.recordLobby(meta);
    await this.broadcastLobby(meta);
    return false;
  }

  private async markSeen(id: string): Promise<void> {
    const seen = (await this.d.store.get<Record<string, number>>("seen")) ?? {};
    seen[id] = this.d.now();
    await this.d.store.put("seen", seen);
  }

  /** A ping or a new connection of a player in the lobby: they are still there. */
  touch(who: Identity): Promise<void> {
    return this.serial(async () => {
      const meta = await this.meta();
      if (meta?.status === "lobby" && meta.joined.includes(who.id)) await this.markSeen(who.id);
    });
  }

  private async start(meta: Meta): Promise<void> {
    meta.options = { ...meta.options, seed: this.d.newSeed() };
    const res = await this.d.engine.newGame(meta.options);
    // Decision D28: the seats are drawn now, so neither the host nor the order of joining decides who sits where. (The engine draws the first player.)
    meta.seats = shuffledSeats(meta.seats, meta.options.seed ?? 0);
    meta.status = "playing";
    meta.startedAt = this.d.now();
    await this.d.store.put("state", res.state);
    await this.d.store.put("logcount", 0);
    await this.d.store.put("clock", clocks.initialClock(meta.clock, meta.seats.length));
    await this.d.store.put("meta", meta);
    await this.d.sink.recordStart(meta);
    await this.runClock(meta, res.state);
    await this.broadcastViews();
    this.archiveSoon();
  }

  // --- play ----------------------------------------------------------------------------------------------------------------

  /** `seq` is the number of actions the client has seen; it makes a repeated or late message harmless. */
  submit(who: Identity, seq: number, action: Action): Promise<SubmitResult> {
    return this.serial(() => this.doSubmit(who, seq, action));
  }

  private async doSubmit(who: Identity, seq: number, action: Action): Promise<SubmitResult> {
    const meta = await this.meta();
    if (meta === undefined || meta.status !== "playing") return fail("not_playing", "the game is not being played");
    const seat = meta.seats.findIndex((s) => s?.id === who.id);
    if (seat < 0) return fail("not_seated", "you are not a player of this game");
    const state = await this.state();
    const count = (await this.d.store.get<number>("logcount")) ?? 0;
    if (seq !== count) return fail("stale", `the game is at action ${count}, not ${seq}`);
    if (toAct(state) !== seat) return fail("not_your_turn", "it is not your turn");
    let res: Awaited<ReturnType<Engine["apply"]>>;
    try {
      res = await this.d.engine.apply(state, action);
    } catch (e) {
      if (e instanceof IllegalAction) return { ok: false, code: "illegal", message: e.message, legal: e.legal };
      throw e;
    }
    const now = this.d.now();
    const entry: LogEntry = { seq: count, seat, action, at: now, events: res.events };
    await this.d.store.put(logKey(count), entry);
    await this.d.store.put("logcount", count + 1);
    await this.d.store.put("state", res.state);
    for (const c of this.d.connections()) c.send({ t: "log", from: count, entries: [publicEntry(entry)] });
    const clock = (await this.d.store.get<clocks.ClockState>("clock")) ?? clocks.initialClock(meta.clock, meta.seats.length);
    await this.d.store.put("clock", clocks.stop(meta.clock, clock, now));
    if (res.state.phase === "finished") {
      await this.finish(meta, res.state, "completed");
      return { ok: true };
    }
    await this.runClock(meta, res.state);
    await this.broadcastViews();
    this.archiveSoon();
    return { ok: true };
  }

  resign(who: Identity): Promise<SubmitResult> {
    return this.serial(() => this.doResign(who));
  }

  private async doResign(who: Identity): Promise<SubmitResult> {
    const meta = await this.meta();
    if (meta === undefined || meta.status !== "playing") return fail("not_playing", "the game is not being played");
    const seat = meta.seats.findIndex((s) => s?.id === who.id);
    if (seat < 0) return fail("not_seated", "you are not a player of this game");
    await this.finish(meta, await this.state(), "resigned", seat);
    return { ok: true };
  }

  /** Called when the alarm rings: in a game of 1 or 2 players the player whose time is up forfeits (docs/PLAN.md section 6). */
  onAlarm(): Promise<void> {
    return this.serial(() => this.doAlarm());
  }

  private async doAlarm(): Promise<void> {
    const meta = await this.meta();
    if (meta === undefined) return;
    if (meta.status === "finished") {
      this.archiveSoon(); // an archive write failed earlier: try again
      return;
    }
    if (meta.status === "lobby") {
      // players who have not pinged for a minute have left; a lobby that empties this way is destroyed
      const seen = (await this.d.store.get<Record<string, number>>("seen")) ?? {};
      const now = this.d.now();
      for (const id of [...meta.joined]) {
        if (now - (seen[id] ?? 0) > LOBBY_GRACE_MS && (await this.removeFromLobby(meta, id))) return;
      }
      await this.d.setAlarm(now + LOBBY_CHECK_MS);
      return;
    }
    if (meta.status !== "playing" || meta.seats.length >= KICK_FROM_PLAYERS) return;
    const clock = await this.d.store.get<clocks.ClockState>("clock");
    if (clock === undefined) return;
    const seat = clocks.expired(meta.clock, clock, this.d.now());
    if (seat !== null) await this.finish(meta, await this.state(), "timeout", seat);
    else await this.d.setAlarm(clocks.deadline(meta.clock, clock));
  }

  /** Decision D24: in a game of 3 or 4 players any other player can kick a player whose clock is in the negative. The game ends and the others all share first place. */
  kick(who: Identity, target: number): Promise<SubmitResult> {
    return this.serial(async () => {
      const meta = await this.meta();
      if (meta === undefined || meta.status !== "playing") return fail("not_playing", "the game is not being played");
      const seat = meta.seats.findIndex((s) => s?.id === who.id);
      if (seat < 0) return fail("not_seated", "you are not a player of this game");
      if (meta.seats.length < KICK_FROM_PLAYERS) return fail("no_kick", "players can only be kicked in games of 3 or 4 players");
      if (!Number.isInteger(target) || target < 0 || target >= meta.seats.length || target === seat) {
        return fail("bad_target", "choose another player");
      }
      const clock = await this.d.store.get<clocks.ClockState>("clock");
      if (clock === undefined || !clocks.overdue(meta.clock, clock, this.d.now(), target)) {
        return fail("not_overdue", "that player's clock is not in the negative");
      }
      await this.finish(meta, await this.state(), "kicked", target);
      return { ok: true };
    });
  }

  private async runClock(meta: Meta, state: GameState): Promise<void> {
    const actor = toAct(state);
    const base = (await this.d.store.get<clocks.ClockState>("clock")) ?? clocks.initialClock(meta.clock, meta.seats.length);
    const clock = actor === null ? base : clocks.start(base, actor, this.d.now());
    await this.d.store.put("clock", clock);
    // Only a game of 1 or 2 players ends at once when a clock runs out; in the others the players decide (kick).
    await this.d.setAlarm(meta.seats.length < KICK_FROM_PLAYERS ? clocks.deadline(meta.clock, clock) : null);
  }

  private async finish(meta: Meta, state: GameState, reason: EndReason, forfeit?: number): Promise<void> {
    const players = meta.seats.length;
    const scores = Array.from({ length: players }, (_, i) => state.players[i]?.score ?? 0);
    const totals = state.final_scores.length > 0 ? Array.from({ length: players }, (_, i) => finalTotal(state, i, scores[i] ?? 0)) : scores;
    const ranking = reason === "kicked" ? rankKicked(totals, forfeit ?? 0) : rank(totals, forfeit);
    const winners = reason === "completed" ? winnersOf(state, players, ranking) : ranking.filter((r) => r.rank === 1).map((r) => r.seat);
    const result: Result = { reason, ranking, winners, finalScores: state.final_scores, ...(forfeit === undefined ? {} : { forfeit }) };
    meta.status = "finished";
    meta.endedAt = this.d.now();
    meta.result = result;
    await this.d.store.put("meta", meta);
    await this.d.setAlarm(null);
    const log = await this.d.store.list<LogEntry>("log:");
    // A rated game with registered players always counts, however it ends and however short it was (decision D24).
    const counts = meta.rated && meta.seats.every((s) => s?.registered === true) && players >= 2;
    await this.d.store.put("counted", counts);
    await this.d.sink.recordEnd({ meta, result, actions: log.length, rated: counts }, log);
    await this.broadcastViews();
    for (const c of this.d.connections()) c.send({ t: "ended", result });
    this.archiveSoon();
  }

  // --- the archive (decision D25) --------------------------------------------------------------------------------------------

  /** Write what is not yet in the archive, in the background. A failure is retried at the next action, and every minute once the game is over. */
  private archiveSoon(): void {
    const run = this.archiveQueue.then(() => this.flushArchive()).catch(() => undefined);
    this.archiveQueue = run;
    this.d.defer?.(run);
  }

  /** Resolves when the archive writes started so far are over (the tests wait for it). */
  archived(): Promise<unknown> {
    return this.archiveQueue;
  }

  private async flushArchive(): Promise<void> {
    const meta = await this.meta();
    if (meta === undefined || (meta.status !== "playing" && meta.status !== "finished")) return;
    const progress = (await this.d.store.get<ArchiveProgress>("archive")) ?? { header: false, actions: 0, done: false };
    if (progress.done) return;
    try {
      if (!progress.header) {
        await this.d.archive.put(headerPath(meta), headerOf(meta));
        progress.header = true;
        await this.d.store.put("archive", progress);
      }
      const count = (await this.d.store.get<number>("logcount")) ?? 0;
      while (progress.actions < count) {
        const entry = await this.d.store.get<LogEntry>(logKey(progress.actions));
        if (entry === undefined) throw new Error(`action ${progress.actions} is missing from the log`);
        await this.d.archive.put(actionPath(meta, progress.actions), entry);
        progress.actions++;
        await this.d.store.put("archive", progress);
      }
      if (meta.status === "finished") {
        const replay = await this.replayFile();
        if (replay?.result) await this.d.archive.put(resultPath(meta), replay.result);
        if (replay) await this.d.archive.put(replayPath(meta), replay);
        progress.done = true;
        await this.d.store.put("archive", progress);
      }
    } catch (e) {
      console.error(`archive of game ${meta.id} failed, will retry:`, e);
      if (meta.status === "finished") await this.d.setAlarm(this.d.now() + ARCHIVE_RETRY_MS);
    }
  }

  /** The whole game as a replay file, for a finished game only (a game in progress would give away the seed). */
  async replayFile(): Promise<ReplayFile | null> {
    const meta = await this.meta();
    if (meta === undefined || meta.status !== "finished") return null;
    return replayOf(meta, await this.d.store.list<LogEntry>("log:"), (await this.d.store.get<boolean>("counted")) ?? false);
  }

  // --- connections ---------------------------------------------------------------------------------------------------------

  /** Send a new connection what it needs to see now. */
  async connect(conn: Connection): Promise<void> {
    const meta = await this.meta();
    if (meta === undefined) {
      conn.send({ t: "error", code: "unknown_game", message: "no such game" });
      return;
    }
    if (meta.status === "lobby") conn.send(lobbyMessage(meta));
    else {
      await this.sendView(conn, meta);
      const log = await this.d.store.list<LogEntry>("log:");
      conn.send({ t: "log", from: 0, entries: log.map(publicEntry) });
    }
  }

  /** What the clients are told: the view of each seat, or the spectator view. */
  private async broadcastViews(): Promise<void> {
    const meta = await this.meta();
    if (meta === undefined) return;
    await Promise.all(this.d.connections().map((c) => this.sendView(c, meta)));
  }

  private async sendView(conn: Connection, meta: Meta): Promise<void> {
    const state = await this.state();
    const seat = conn.who === null ? -1 : meta.seats.findIndex((s) => s?.id === conn.who);
    const view = await this.d.engine.project(state, seat >= 0 ? seat : null);
    const clock = await this.d.store.get<clocks.ClockState>("clock");
    const remaining = clock === undefined ? null : clocks.remaining(meta.clock, clock, this.d.now(), meta.seats.length);
    conn.send({
      t: "view",
      seq: (await this.d.store.get<number>("logcount")) ?? 0,
      status: meta.status,
      view,
      names: meta.seats.map((s) => s?.name ?? ""),
      remaining,
    });
  }

  private async broadcastLobby(meta: Meta): Promise<void> {
    for (const c of this.d.connections()) c.send(lobbyMessage(meta));
  }

  async log(): Promise<LogEntry[]> {
    return this.d.store.list<LogEntry>("log:");
  }

  async meta(): Promise<Meta | undefined> {
    return this.d.store.get<Meta>("meta");
  }

  /** The game as anybody may see it: the seed is kept back until the game is over, because it gives the hidden information away (CLAUDE.md rule 6). */
  async publicMeta(): Promise<Meta | undefined> {
    const meta = await this.meta();
    if (meta === undefined || meta.status === "finished") return meta;
    const { seed: _seed, ...options } = meta.options;
    return { ...meta, options: options as Meta["options"] };
  }

  /** The seat of an identity in this game, or null. */
  async seatOf(who: Identity): Promise<number | null> {
    const meta = await this.meta();
    const i = meta?.seats.findIndex((s) => s?.id === who.id) ?? -1;
    return i >= 0 ? i : null;
  }

  private async state(): Promise<GameState> {
    const s = await this.d.store.get<GameState>("state");
    if (s === undefined) throw new Error("the game has no state");
    return s;
  }
}

function fail(code: string, message: string): { ok: false; code: string; message: string } {
  return { ok: false, code, message };
}

function lobbyMessage(meta: Meta): ServerMessage {
  return {
    t: "lobby",
    status: meta.status,
    seats: meta.seats.map((s) => (s === null ? null : { name: s.name })),
    host: meta.seats.find((s) => s?.id === meta.host)?.name ?? null,
    rated: meta.rated,
    clock: meta.clock,
  };
}

function finalTotal(state: GameState, seat: number, fallback: number): number {
  const row = state.final_scores.find((r) => (r as { player?: number }).player === seat) as { total?: number } | undefined;
  return row?.total ?? fallback;
}

/** Rank seats by score, best first; equal scores share a rank; a forfeiting seat is last (docs/PLAN.md section 6). */
export function rank(totals: number[], forfeit?: number): RankedSeat[] {
  const contenders = totals.map((score, seat) => ({ seat, score })).filter((x) => x.seat !== forfeit);
  contenders.sort((a, b) => b.score - a.score);
  const out: RankedSeat[] = [];
  contenders.forEach((c, i) => {
    const prev = out[i - 1];
    out.push({ seat: c.seat, score: c.score, rank: prev !== undefined && prev.score === c.score ? prev.rank : i + 1 });
  });
  if (forfeit !== undefined) out.push({ seat: forfeit, score: totals[forfeit] ?? 0, rank: contenders.length + 1 });
  return out.sort((a, b) => a.seat - b.seat);
}

/** A player was kicked: the others all share first place and the kicked player is behind them. */
export function rankKicked(totals: number[], kicked: number): RankedSeat[] {
  return totals.map((score, seat) => ({ seat, score, rank: seat === kicked ? 2 : 1 }));
}

/** The engine names the winners among its players; in the solo game the rival is not a seat, so the human wins or loses. */
function winnersOf(state: GameState, players: number, ranking: RankedSeat[]): number[] {
  if (state.rival !== null && state.rival !== undefined) return state.winners.filter((w) => w < players);
  return ranking.filter((r) => r.rank === 1).map((r) => r.seat);
}
