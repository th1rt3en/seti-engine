// The checks of what comes in from outside before the room or the engine sees it: the options and the clock of a new table, and the messages of a WebSocket.
// Only known keys with values of the right type and size get through; anything else is refused, never repaired.
import type { Options } from "@seti/protocol";
import type { ClockSettings } from "./clock.js";

const BOOLEAN_OPTIONS = [
  "beginner_organizations",
  "expansion",
  "neutral_quick_start",
  "organizations",
  "promo_cards",
  "promo_set_2",
  "sandbox",
  "simul_setup",
] as const;
const KNOWN = new Set<string>(["players", "difficulty", "seed", "sandbox_species", ...BOOLEAN_OPTIONS]);

/** The most a WebSocket message of a player may weigh: a move is a few hundred bytes. */
export const MAX_MESSAGE_BYTES = 8192;

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);

export function validOptions(o: unknown): o is Options {
  if (!isRecord(o)) return false;
  if (Object.keys(o).some((k) => !KNOWN.has(k))) return false;
  if (!Number.isInteger(o.players) || (o.players as number) < 1 || (o.players as number) > 4) return false;
  if (o.difficulty !== undefined && (!Number.isInteger(o.difficulty) || (o.difficulty as number) < 1 || (o.difficulty as number) > 5))
    return false;
  if (o.seed !== undefined && !(Number.isSafeInteger(o.seed) && (o.seed as number) >= 0)) return false;
  for (const k of BOOLEAN_OPTIONS) if (o[k] !== undefined && typeof o[k] !== "boolean") return false;
  if (o.sandbox_species !== undefined) {
    const s = o.sandbox_species;
    if (!Array.isArray(s) || s.length > 2 || s.some((x) => x !== null && !(typeof x === "string" && /^[a-z_]{1,24}$/.test(x))))
      return false;
  }
  return true;
}

const positive = (v: unknown): boolean => typeof v === "number" && Number.isFinite(v) && v > 0 && v <= 7 * 24 * 3600 * 1000;

export function validClock(c: unknown): c is ClockSettings {
  if (!isRecord(c)) return false;
  if (c.kind === "none") return true;
  if (c.kind === "per_turn") return positive(c.ms);
  return (
    c.kind === "bank" &&
    positive(c.initialMs) &&
    typeof c.incrementMs === "number" &&
    Number.isFinite(c.incrementMs) &&
    c.incrementMs >= 0 &&
    c.incrementMs <= 24 * 3600 * 1000
  );
}

/** A message of a WebSocket as text, or null when it is too big or not a text (a message of a player is a small JSON text). */
export function messageText(message: string | ArrayBuffer): string | null {
  if (typeof message === "string") return message.length <= MAX_MESSAGE_BYTES ? message : null;
  return message.byteLength <= MAX_MESSAGE_BYTES ? new TextDecoder().decode(message) : null;
}
