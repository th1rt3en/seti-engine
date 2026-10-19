// The log of moves that every client may see while a game is played (CLAUDE.md rule 6: hidden information never leaves the server unprojected).
// An entry of the action log holds the action and the events the engine reported. Both are public except the identity of the cards that go to
// a player's hand or income without being shown: a tucked card, the end-of-round card a player takes, an Exertian card played face down.
import type { LogEntry } from "./room.js";

export interface PublicEntry {
  seq: number;
  seat: number;
  action: Record<string, unknown>;
  events: Record<string, unknown>[];
}

/** Actions whose `card` is not shown to the other players. */
const HIDDEN_CARD_ACTIONS = new Set(["tuck", "take_round_card", "play_exertian", "pol_pick"]);
/** Events whose `card` is not shown. */
const HIDDEN_CARD_EVENTS = new Set(["tuck"]);

const without = <T extends Record<string, unknown>>(o: T, key: string): T => {
  const { [key]: _hidden, ...rest } = o;
  return rest as T;
};

/** The card drawn from the deck is told to the player who drew it only. */
export function publicEntry(e: LogEntry, viewer: number | null = null): PublicEntry {
  const action = HIDDEN_CARD_ACTIONS.has(String((e.action as Record<string, unknown>).type))
    ? without(e.action as Record<string, unknown>, "card")
    : e.action;
  const events = e.events.map((ev) =>
    HIDDEN_CARD_EVENTS.has(String(ev.type)) || (ev.type === "draw_card" && ev.player !== viewer) ? without(ev, "card") : ev,
  );
  return { seq: e.seq, seat: e.seat, action: action as Record<string, unknown>, events };
}
