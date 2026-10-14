// The site's calls to the Worker (create, join, leave, read a game). Each call carries a short-lived token for the user.
import { type User, mintToken } from "./auth";
import { type Config, loadConfig } from "./config";

export interface Clock {
  kind: "none" | "per_turn" | "bank";
  ms?: number;
  initialMs?: number;
  incrementMs?: number;
}

export interface NewGame {
  options: { players: number; difficulty?: number; promo_cards?: boolean; sandbox?: boolean; sandbox_species?: (string | null)[] };
  clock: Clock;
  rated: boolean;
}

export type WorkerReply = { ok: true; [k: string]: unknown } | { ok: false; code: string; message: string };

async function call(user: User, path: string, method: string, body: unknown, cfg: Config, fetcher: typeof fetch): Promise<WorkerReply> {
  const token = await mintToken(user, cfg);
  const res = await fetcher(`${cfg.workerUrl}${path}`, {
    method,
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  return (await res.json()) as WorkerReply;
}

export const createGame = (user: User, game: NewGame, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, "/games", "POST", game, cfg, fetcher);
export const joinGame = (user: User, id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/join`, "POST", undefined, cfg, fetcher);
export const leaveGame = (user: User, id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/leave`, "POST", undefined, cfg, fetcher);

/** Public data of a game (no token needed). */
export async function gameMeta(id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch): Promise<Record<string, unknown> | null> {
  const res = await fetcher(`${cfg.workerUrl}/games/${id}`);
  return res.ok ? ((await res.json()) as Record<string, unknown> | null) : null;
}

export async function gameLog(
  id: string,
  cfg = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<{ action: Record<string, unknown> }[]> {
  const res = await fetcher(`${cfg.workerUrl}/games/${id}/log`);
  return res.ok ? ((await res.json()) as { action: Record<string, unknown> }[]) : [];
}

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

/** The clock presets of the lobby (decisions D13, D26, D34). `none` is offered in both modes. */
export type ClockMode = "realtime" | "turnbased";
export const CLOCK_PRESETS: Record<string, { label: string; mode: ClockMode | "both"; clock: Clock }> = {
  none: { label: "No time control", mode: "both", clock: { kind: "none" } },
  // Decision D26: three real-time speeds. The starting time is also the maximum; every turn adds the increment. Values set by the owner.
  fast: { label: "Fast: 5 min, +1 min 30 s per turn", mode: "realtime", clock: { kind: "bank", initialMs: 5 * MIN, incrementMs: 90_000 } },
  normal: {
    label: "Normal: 7 min 30 s, +2 min 30 s per turn",
    mode: "realtime",
    clock: { kind: "bank", initialMs: 450_000, incrementMs: 150_000 },
  },
  slow: {
    label: "Slow: 10 min, +3 min 30 s per turn",
    mode: "realtime",
    clock: { kind: "bank", initialMs: 10 * MIN, incrementMs: 210_000 },
  },
  // Decision D34: three turn-based speeds, in days. The same bank clock: the starting time is the most a bank holds and each turn adds the increment.
  tb_fast: { label: "Fast: 2 days, +6 h per turn", mode: "turnbased", clock: { kind: "bank", initialMs: 2 * DAY, incrementMs: 6 * HOUR } },
  tb_normal: {
    label: "Normal: 3 days, +9 h per turn",
    mode: "turnbased",
    clock: { kind: "bank", initialMs: 3 * DAY, incrementMs: 9 * HOUR },
  },
  tb_slow: {
    label: "Slow: 4 days, +12 h per turn",
    mode: "turnbased",
    clock: { kind: "bank", initialMs: 4 * DAY, incrementMs: 12 * HOUR },
  },
};

export interface ReplayData {
  format: string;
  header: {
    id: string;
    options: Record<string, unknown>;
    clock: Clock;
    rated: boolean;
    seats: { seat: number; name: string; registered: boolean }[];
    startedAt: number;
  };
  actions: { seq: number; seat: number; action: Record<string, unknown>; at: number; events: Record<string, unknown>[] }[];
  result: {
    status: string;
    endedAt: number;
    result: { reason: string; forfeit?: number; winners: number[]; ranking: { seat: number; rank: number; score: number }[] };
    ratedCounted: boolean;
  } | null;
}

/** Everything needed to replay a finished game (the Worker refuses while the game is on, because the seed would give the hands away). */
export async function gameReplay(id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch): Promise<ReplayData | null> {
  const res = await fetcher(`${cfg.workerUrl}/games/${id}/replay`);
  return res.ok ? ((await res.json()) as ReplayData) : null;
}
