// The engine service as the Worker sees it (docs/deploy-engine.md).
import type { GameState, Options, StepResult, View } from "@seti/protocol";

import type { Signer } from "./engineAuth.js";

export type Action = Record<string, unknown>;

export class IllegalAction extends Error {
  constructor(
    message: string,
    public readonly legal: Action[],
  ) {
    super(message);
  }
}

/** The statistics of a game that was played to its end (the engine's stats.py): the counters of each player. */
export interface GameStats {
  version: number;
  expansion: boolean;
  species: string[];
  rounds: number;
  players: { seat: number; org: string | null; org_offered: string[]; counters: Record<string, number> }[];
}

export interface Engine {
  newGame(options: Options): Promise<StepResult>;
  /** Throws `IllegalAction` for a move that is not legal. */
  apply(state: GameState, action: Action): Promise<StepResult>;
  /** What `viewer` may see of the state (null for a spectator). */
  project(state: GameState, viewer: number | null): Promise<View>;
  /** The statistics of a finished game, from its options and its actions (the engine replays it). */
  stats?(options: Options, actions: Action[], rngEncoding?: "exact" | "double"): Promise<GameStats>;
}

export class HttpEngine implements Engine {
  private readonly fetcher: typeof fetch;

  constructor(
    private readonly baseUrl: string,
    fetcher?: typeof fetch,
    private readonly sign?: Signer,
  ) {
    // The global fetch must be called without this object as its `this` (Workers throw "Illegal invocation" otherwise).
    this.fetcher = fetcher ?? ((input, init) => fetch(input, init));
  }

  private async post<T>(path: string, body: unknown): Promise<{ status: number; json: T }> {
    const payload = JSON.stringify(body);
    const res = await this.fetcher(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", ...(this.sign ? await this.sign("POST", path, payload) : {}) },
      body: payload,
    });
    return { status: res.status, json: (await res.json()) as T };
  }

  async newGame(options: Options): Promise<StepResult> {
    const { status, json } = await this.post<StepResult>("/new", { options });
    if (status !== 200) throw new Error(`engine /new failed with ${status}`);
    return json;
  }

  async apply(state: GameState, action: Action): Promise<StepResult> {
    const { status, json } = await this.post<StepResult & { message?: string }>("/apply", { state, action });
    if (status === 422) throw new IllegalAction(json.message ?? "illegal action", json.legal);
    if (status !== 200) throw new Error(`engine /apply failed with ${status}`);
    return json;
  }

  async project(state: GameState, viewer: number | null): Promise<View> {
    const { status, json } = await this.post<View>("/project", { state, viewer });
    if (status !== 200) throw new Error(`engine /project failed with ${status}`);
    return json;
  }

  async stats(options: Options, actions: Action[], rngEncoding: "exact" | "double" = "exact"): Promise<GameStats> {
    const { status, json } = await this.post<GameStats>("/stats", { options, actions, rng_encoding: rngEncoding });
    if (status !== 200) throw new Error(`engine /stats failed with ${status}`);
    return json;
  }
}
