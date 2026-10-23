// Test doubles: an in-memory store, a scripted engine and a recording sink.
import type { GameState, Options, StepResult, View } from "@seti/protocol";
import type { Archive } from "../src/core/archive.js";
import type { Identity } from "../src/core/auth.js";
import { type Action, type Engine, type GameStats, IllegalAction } from "../src/core/engine.js";
import {
  type BotClient,
  type BotReply,
  type BotRequest,
  type Connection,
  type Deps,
  type GameRecord,
  GameRoom,
  type LogEntry,
  type Meta,
  type Result,
  type ResultSink,
  type ServerMessage,
  type Store,
} from "../src/core/room.js";

export class MemoryStore implements Store {
  readonly data = new Map<string, unknown>();
  async get<T>(key: string): Promise<T | undefined> {
    const v = this.data.get(key);
    return v === undefined ? undefined : (structuredClone(v) as T);
  }
  async put(key: string, value: unknown): Promise<void> {
    this.data.set(key, structuredClone(value));
  }
  async clear(): Promise<void> {
    this.data.clear();
  }
  async list<T>(prefix: string): Promise<T[]> {
    return [...this.data.keys()]
      .filter((k) => k.startsWith(prefix))
      .sort()
      .map((k) => structuredClone(this.data.get(k)) as T);
  }
}

/** A tiny game: each player in turn scores or ends the turn; the game ends when `last` actions have been played. */
export class FakeEngine implements Engine {
  constructor(private readonly last = 6) {}
  private make(players: number, played: number, current: number, scores: number[]): GameState {
    const finished = played >= this.last;
    return {
      phase: finished ? "finished" : "play",
      pending: [],
      current_player: current,
      players: scores.map((score, index) => ({ index, score })),
      final_scores: finished ? scores.map((s, player) => ({ player, total: s })) : [],
      winners: finished ? [scores.indexOf(Math.max(...scores))] : [],
      rival: null,
      played,
    } as unknown as GameState;
  }
  async newGame(options: Options): Promise<StepResult> {
    const state = this.make(Math.max(options.players, 1), 0, 0, Array(Math.max(options.players, 1)).fill(0));
    return { state, events: [], legal: [{ type: "score" }] } as unknown as StepResult;
  }
  async apply(state: GameState, action: Action): Promise<StepResult> {
    const s = state as unknown as { played: number; current_player: number; players: { score: number }[] };
    if (action.type !== "score" && action.type !== "pass") throw new IllegalAction("not a move", [{ type: "score" }]);
    const scores = s.players.map((p, i) => p.score + (action.type === "score" && i === s.current_player ? 1 : 0));
    const next = this.make(s.players.length, s.played + 1, (s.current_player + 1) % s.players.length, scores);
    return { state: next, events: [], legal: [{ type: "score" }] } as unknown as StepResult;
  }
  async stats(options: Options, actions: Action[]): Promise<GameStats> {
    return {
      version: 1,
      expansion: false,
      species: ["anomalies", "mascamites"],
      rounds: 5,
      players: Array.from({ length: Math.max(options.players, 1) }, (_, seat) => ({
        seat,
        org: null,
        org_offered: [],
        counters: { "action.score": actions.filter((a) => a.type === "score").length },
      })),
    };
  }
  async project(state: GameState, viewer: number | null): Promise<View> {
    return {
      viewer,
      state,
      counts: {},
      to_act: state.current_player,
      legal: viewer === state.current_player ? [{ type: "score" }] : [],
    } as unknown as View;
  }
}

export class RecordingSink implements ResultSink {
  lobbies: Meta[] = [];
  starts: Meta[] = [];
  removed: string[] = [];
  async removeLobby(id: string): Promise<void> {
    this.removed.push(id);
  }
  async recordLobby(meta: Meta): Promise<void> {
    this.lobbies.push(structuredClone(meta));
  }
  ends: { rec: GameRecord; log: LogEntry[] }[] = [];
  async recordStart(meta: Meta): Promise<void> {
    this.starts.push(structuredClone(meta));
  }
  async recordEnd(rec: GameRecord, log: LogEntry[]): Promise<void> {
    this.ends.push({ rec: structuredClone(rec), log });
  }
  statsRecorded: { meta: Meta; stats: GameStats }[] = [];
  async recordStats(meta: Meta, _result: Result, stats: GameStats): Promise<void> {
    this.statsRecorded.push({ meta: structuredClone(meta), stats });
  }
  cancelled: Meta[] = [];
  async recordCancelled(meta: Meta): Promise<void> {
    this.cancelled.push(structuredClone(meta));
  }
}

export class RecordingArchive implements Archive {
  readonly files = new Map<string, unknown>();
  /** Writes fail while this is set. */
  failing = false;
  async put(path: string, body: unknown): Promise<void> {
    if (this.failing) throw new Error("the archive is down");
    this.files.set(path, structuredClone(body));
  }
}

export class Conn implements Connection {
  readonly got: ServerMessage[] = [];
  constructor(
    readonly id: string,
    readonly who: string | null,
  ) {}
  send(msg: ServerMessage): void {
    this.got.push(msg);
  }
  last(type: ServerMessage["t"]): ServerMessage | undefined {
    return [...this.got].reverse().find((m) => m.t === type);
  }
}

export const alice: Identity = { id: "u-alice", name: "Alice", registered: true };
export const bob: Identity = { id: "u-bob", name: "Bob", registered: true };
export const cy: Identity = { id: "u-cy", name: "Cy", registered: true };
export const guest: Identity = { id: "g-1", name: "Guest", registered: false };

/** An AI service that always scores; it keeps the requests it got and can be told to fail. */
export class FakeBot implements BotClient {
  requests: BotRequest[] = [];
  failing = false;
  async move(req: BotRequest): Promise<BotReply> {
    this.requests.push(structuredClone(req));
    if (this.failing) throw new Error("the AI service is down");
    return { action: { type: "score" }, plan: [{ type: "score" }] };
  }
}

export function makeRoom(opts: { last?: number; now?: () => number; seed?: number; bot?: BotClient; engine?: Engine } = {}) {
  const store = new MemoryStore();
  const sink = new RecordingSink();
  const archive = new RecordingArchive();
  const conns: Connection[] = [];
  const alarms: (number | null)[] = [];
  let time = 1_000_000;
  const deps: Deps = {
    store,
    engine: opts.engine ?? new FakeEngine(opts.last ?? 6),
    ...(opts.bot ? { bot: opts.bot } : {}),
    sink,
    archive,
    now: opts.now ?? (() => time),
    newSeed: () => opts.seed ?? 4242,
    connections: () => conns,
    setAlarm: async (at) => {
      alarms.push(at);
    },
  };
  const room = new GameRoom(deps);
  return {
    room,
    store,
    sink,
    archive,
    conns,
    alarms,
    advance: (ms: number) => {
      time += ms;
    },
    clock: () => time,
  };
}
