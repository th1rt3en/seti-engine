// Game clocks (decision D13). A game is untimed, has a time limit per turn (turn-based play, hours or days),
// or gives every player a time bank with an increment (real-time play).
// Usually the clock runs for one player. In the simultaneous setup of the organization module (EXP-ORG-14) it runs for every player who has not locked in,
// each with the time of its own period.

export type ClockSettings = { kind: "none" } | { kind: "per_turn"; ms: number } | { kind: "bank"; initialMs: number; incrementMs: number };

export interface Run {
  seat: number;
  /** When the running period of this seat started (ms since the epoch). */
  since: number;
}

export interface ClockState {
  /** The players the clock is running for (none when it is stopped). */
  runs: Run[];
  /** Time left per player, for the bank clock. */
  bank: number[];
}

export function initialClock(settings: ClockSettings, players: number): ClockState {
  return { runs: [], bank: settings.kind === "bank" ? Array(players).fill(settings.initialMs) : [] };
}

/** A clock as it was stored by the version that ran for one player only (`running`, `since`). */
export function normalize(raw: ClockState | { running: number | null; since: number; bank: number[] }): ClockState {
  if ("runs" in raw) return raw;
  return { runs: raw.running === null ? [] : [{ seat: raw.running, since: raw.since }], bank: raw.bank };
}

/** Run the clock for these players at `now`: a player whose clock already runs keeps its period, the others start one; nobody else runs. */
export function start(clock: ClockState, players: number | number[], now: number): ClockState {
  const seats = Array.isArray(players) ? players : [players];
  const kept = clock.runs.filter((r) => seats.includes(r.seat));
  const added = seats.filter((s) => !kept.some((r) => r.seat === s)).map((seat) => ({ seat, since: now }));
  return { ...clock, runs: [...kept, ...added] };
}

/** Stop the clock of `seat` (all running clocks without it) after the player acted: the bank loses the elapsed time and gains the increment. */
export function stop(settings: ClockSettings, clock: ClockState, now: number, seat?: number): ClockState {
  const stopped = clock.runs.filter((r) => seat === undefined || r.seat === seat);
  const rest = clock.runs.filter((r) => seat !== undefined && r.seat !== seat);
  if (settings.kind !== "bank") return { ...clock, runs: rest };
  const bank = [...clock.bank];
  for (const r of stopped) {
    const left = bank[r.seat] ?? 0;
    // The starting time is also the most a bank can hold (decision D26). It may stay negative: see `overdue`.
    bank[r.seat] = Math.min(settings.initialMs, left - (now - r.since) + settings.incrementMs);
  }
  return { runs: rest, bank };
}

function endOf(settings: ClockSettings, clock: ClockState, r: Run): number | null {
  if (settings.kind === "per_turn") return r.since + settings.ms;
  if (settings.kind === "bank") return r.since + (clock.bank[r.seat] ?? 0);
  return null;
}

/** When the first running player runs out of time, or null when no deadline applies. */
export function deadline(settings: ClockSettings, clock: ClockState): number | null {
  const ends = clock.runs.map((r) => endOf(settings, clock, r)).filter((x): x is number => x !== null);
  return ends.length === 0 ? null : Math.min(...ends);
}

/** The player whose time has run out at `now` (the one who ran out first), if any. */
export function expired(settings: ClockSettings, clock: ClockState, now: number): number | null {
  let found: { seat: number; at: number } | null = null;
  for (const r of clock.runs) {
    const at = endOf(settings, clock, r);
    if (at !== null && now >= at && (found === null || at < found.at)) found = { seat: r.seat, at };
  }
  return found?.seat ?? null;
}

/** Time left for every player at `now` (what a client shows); null without a clock. */
export function remaining(settings: ClockSettings, clock: ClockState, now: number, players: number): (number | null)[] | null {
  if (settings.kind === "none") return null;
  return Array.from({ length: players }, (_, i) => {
    const run = clock.runs.find((r) => r.seat === i);
    if (settings.kind === "per_turn") return run === undefined ? null : run.since + settings.ms - now;
    const ms = clock.bank[i] ?? 0;
    return run === undefined ? ms : ms - (now - run.since);
  });
}

/** True when the clock of `seat` is in the negative at `now` (decision D24: in a game of 3 or 4 players another player may then kick it). */
export function overdue(settings: ClockSettings, clock: ClockState, now: number, seat: number): boolean {
  const all = remaining(settings, clock, now, Math.max(seat + 1, clock.bank.length));
  const left = all?.[seat];
  return left !== null && left !== undefined && left < 0;
}
