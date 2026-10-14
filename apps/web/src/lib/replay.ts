// Replay (decision D8): the seed and the action log of a finished game reproduce every state. The states are computed by the engine
// service on first use and kept in memory for the most recent games.
import type { GameState, View } from "@seti/protocol";
import { type Config, loadConfig } from "./config";
import { engineAuth } from "./engineAuth";

interface StepResult {
  state: GameState;
}

const cache = new Map<string, GameState[]>();
const MAX_CACHED = 8;

async function post<T>(cfg: Config, path: string, body: unknown, fetcher: typeof fetch): Promise<T> {
  const payload = JSON.stringify(body);
  const res = await fetcher(`${cfg.engineUrl}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(await engineAuth(cfg.engineSigningKey, "POST", path, payload)) },
    body: payload,
  });
  if (!res.ok) throw new Error(`engine ${path} answered ${res.status}`);
  return (await res.json()) as T;
}

/** Every state of the game: index 0 is the start, index n the state after the n-th action. */
export async function replayStates(
  id: string,
  options: unknown,
  log: { action: Record<string, unknown> }[],
  cfg: Config = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<GameState[]> {
  const hit = cache.get(id);
  if (hit !== undefined && hit.length === log.length + 1) return hit;
  const first = await post<StepResult>(cfg, "/new", { options }, fetcher);
  const states = [first.state];
  for (const entry of log) {
    const next = await post<StepResult>(cfg, "/apply", { state: states[states.length - 1], action: entry.action }, fetcher);
    states.push(next.state);
  }
  cache.set(id, states);
  if (cache.size > MAX_CACHED) cache.delete(cache.keys().next().value as string);
  return states;
}

/** The view of one state: the spectator's (viewer null, nothing hidden is shown, decision D9) or, once the game is over, a player's. */
export function spectate(
  state: GameState,
  viewer: number | null = null,
  cfg: Config = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<View> {
  return post<View>(cfg, "/project", { state, viewer }, fetcher);
}
