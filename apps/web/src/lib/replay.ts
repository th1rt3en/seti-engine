// Replay (decision D8): the seed and the action log of a finished game reproduce every state. The engine service replays the whole game in one request
// (a fraction of a second) and answers with the view of the step that is asked for and of the step before it. Nothing is worked out here.
import type { View } from "@seti/protocol";
import { type Config, loadConfig } from "./config";
import { engineAuth } from "./engineAuth";

export interface ReplayStep {
  step: number;
  view: View;
  /** The view of the step before, for what has just changed (null at the start). */
  previous: View | null;
}

/**
 * One step of a replay as a seat or the spectator (viewer null) saw it. `rngEncoding` is "double" for a game that was played before the random state
 * of the game was written as a string (the engine then rounds it the way the Worker did); a game that has no value there is such a game.
 */
export async function replayStep(
  options: unknown,
  log: { action: Record<string, unknown> }[],
  step: number,
  viewer: number | null,
  rngEncoding: "exact" | "double" = "double",
  cfg: Config = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<ReplayStep> {
  const path = "/replay/view";
  const payload = JSON.stringify({ options, actions: log.map((e) => e.action), step, viewer, rng_encoding: rngEncoding });
  const res = await fetcher(`${cfg.engineUrl}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...(await engineAuth(cfg.engineSigningKey, "POST", path, payload)) },
    body: payload,
  });
  if (!res.ok) throw new Error(`engine ${path} answered ${res.status}`);
  return (await res.json()) as ReplayStep;
}
