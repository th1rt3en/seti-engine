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
  options: {
    players: number;
    difficulty?: number;
    promo_cards?: boolean;
    promo_set_2?: boolean;
    sandbox?: boolean;
    sandbox_species?: (string | null)[];
    expansion?: boolean;
    organizations?: boolean;
    beginner_organizations?: boolean;
    neutral_quick_start?: boolean;
    /** A seed chosen by the host: friendly games only (the Worker refuses it in a rated game). */
    seed?: number;
  };
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

/** The host starts the game once every seat is taken (the lobby never starts it by itself). */
export const startGame = (user: User, id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/start`, "POST", undefined, cfg, fetcher);

/** The host adds an AI model to the lobby; `consent` is the host's agreement that the game is collected and used for training. */
export const addBot = (user: User, id: string, model: string, consent: boolean, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/bot-add`, "POST", { model, consent }, cfg, fetcher);
export const removeBot = (user: User, id: string, seat: number, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/bot-remove`, "POST", { seat }, cfg, fetcher);

export const resignGame = (user: User, id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch) =>
  call(user, `/games/${id}/resign`, "POST", undefined, cfg, fetcher);

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
    seats: { seat: number; name: string; registered: boolean; num?: number }[];
    startedAt: number;
    /** "double": the game was played before the random state became a string (the engine replays it with the rounding the Worker did). */
    rngEncoding?: "exact" | "double";
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

// --- the administrator (the key is the one that the Worker holds as ADMIN_WORKER_KEY) ---------------------------------------------

export interface AdminGameInfo {
  status: string;
  rated: boolean;
  players: string[];
  createdAt: number;
  /** When something last happened in the game (a move; in a lobby, a player's ping), in ms. */
  lastActivity: number;
  actions: number;
}

async function adminCall(path: string, method: string, cfg: Config, fetcher: typeof fetch, body?: unknown): Promise<unknown> {
  const res = await fetcher(`${cfg.workerUrl}/admin${path}`, {
    method,
    headers: { "x-admin-key": cfg.adminWorkerKey, ...(body === undefined ? {} : { "content-type": "application/json" }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    // the Worker (or what is in front of it) did not answer with JSON: say so instead of failing the page
    return { ok: false, code: "bad_reply", message: `the Worker answered ${res.status} with something that is not JSON` };
  }
}

/** State and last activity of a game, or null when the game is not known to the Worker any more. */
export async function adminGameInfo(id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch): Promise<AdminGameInfo | null> {
  return (await adminCall(`/games/${id}`, "GET", cfg, fetcher)) as AdminGameInfo | null;
}

/** The seed of a game (also while it is played), or null when the Worker does not know the game. */
export async function adminGameSeed(
  id: string,
  cfg = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<{ status: string; seed: number | null; seeded: boolean } | null> {
  return (await adminCall(`/games/${id}/seed`, "GET", cfg, fetcher)) as { status: string; seed: number | null; seeded: boolean } | null;
}

export interface AdminRecent {
  ok: boolean;
  message?: string;
  total?: number;
  recent?: { seq: number; seat: number; action: Record<string, unknown>; at: number }[];
}

/** The last actions of a game that is being played, for the administrator. */
export async function adminRecentActions(id: string, count = 8, cfg = loadConfig(), fetcher: typeof fetch = fetch): Promise<AdminRecent> {
  return (await adminCall(`/games/${id}/recent?count=${count}`, "GET", cfg, fetcher)) as AdminRecent;
}

/** Takes back the last `count` actions of a game that is being played: the game is rebuilt without them and every player gets it as it is. */
export async function adminUndoGame(
  id: string,
  count: number,
  cfg = loadConfig(),
  fetcher: typeof fetch = fetch,
): Promise<WorkerReply & { removed?: number; left?: number }> {
  return (await adminCall(`/games/${id}/undo`, "POST", cfg, fetcher, { count })) as WorkerReply & { removed?: number; left?: number };
}

/** Cancels a lobby or a game that is being played: nobody wins or loses and no rating changes. */
export async function adminCancelGame(id: string, cfg = loadConfig(), fetcher: typeof fetch = fetch): Promise<WorkerReply> {
  return (await adminCall(`/games/${id}/cancel`, "POST", cfg, fetcher)) as WorkerReply;
}
