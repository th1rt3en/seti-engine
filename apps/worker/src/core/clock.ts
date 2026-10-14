// Game clocks (decision D13). A game is untimed, has a time limit per turn (turn-based play, hours or days),
// or gives every player a time bank with an increment (real-time play).

export type ClockSettings = { kind: "none" } | { kind: "per_turn"; ms: number } | { kind: "bank"; initialMs: number; incrementMs: number };

export interface ClockState {
  /** The player the clock is running for, or null when it is stopped. */
  running: number | null;
  /** When the running period started (ms since the epoch). */
  since: number;
  /** Time left per player, for the bank clock. */
  bank: number[];
}

export function initialClock(settings: ClockSettings, players: number): ClockState {
  return { running: null, since: 0, bank: settings.kind === "bank" ? Array(players).fill(settings.initialMs) : [] };
}

/** Start the clock for `player` at `now`. */
export function start(clock: ClockState, player: number, now: number): ClockState {
  return { ...clock, running: player, since: now };
}

/** Stop the running clock after the player acted: the bank loses the elapsed time and gains the increment. */
export function stop(settings: ClockSettings, clock: ClockState, now: number): ClockState {
  if (clock.running === null || settings.kind !== "bank") return { ...clock, running: null };
  const bank = [...clock.bank];
  const left = bank[clock.running] ?? 0;
  // The starting time is also the most a bank can hold (decision D26). It may stay negative: see `overdue`.
  bank[clock.running] = Math.min(settings.initialMs, left - (now - clock.since) + settings.incrementMs);
  return { running: null, since: now, bank };
}

/** When the running player runs out of time, or null when no deadline applies. */
export function deadline(settings: ClockSettings, clock: ClockState): number | null {
  if (clock.running === null) return null;
  if (settings.kind === "per_turn") return clock.since + settings.ms;
  if (settings.kind === "bank") return clock.since + (clock.bank[clock.running] ?? 0);
  return null;
}

/** The player whose time has run out at `now`, if any. */
export function expired(settings: ClockSettings, clock: ClockState, now: number): number | null {
  const d = deadline(settings, clock);
  return d !== null && clock.running !== null && now >= d ? clock.running : null;
}

/** Time left for every player at `now` (what a client shows); null without a clock. */
export function remaining(settings: ClockSettings, clock: ClockState, now: number, players: number): (number | null)[] | null {
  if (settings.kind === "none") return null;
  return Array.from({ length: players }, (_, i) => {
    if (settings.kind === "per_turn") return clock.running === i ? clock.since + settings.ms - now : null;
    const ms = clock.bank[i] ?? 0;
    return i === clock.running ? ms - (now - clock.since) : ms;
  });
}

/** True when the clock of `seat` is in the negative at `now` (decision D24: in a game of 3 or 4 players another player may then kick it). */
export function overdue(settings: ClockSettings, clock: ClockState, now: number, seat: number): boolean {
  const all = remaining(settings, clock, now, Math.max(seat + 1, clock.bank.length));
  const left = all?.[seat];
  return left !== null && left !== undefined && left < 0;
}
