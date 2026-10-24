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

/** The choices of the simultaneous setup stay secret from the other players (EXP-ORG-14): the organization and the quick start cards are shown by the
 * engine when everybody has locked in (the events), not by these moves. */
const SECRET_CHOICES = new Set(["choose_org", "choose_quick"]);

/** Actions whose `card` is not shown to the other players. */
const HIDDEN_CARD_ACTIONS = new Set(["tuck", "setup_tuck", "setup_untuck", "take_round_card", "play_exertian", "pol_pick"]);
/** Events whose `card` is not shown. */
const HIDDEN_CARD_EVENTS = new Set(["tuck", "untuck"]);

const without = <T extends Record<string, unknown>>(o: T, key: string): T => {
  const { [key]: _hidden, ...rest } = o;
  return rest as T;
};

/** The moves of the simultaneous setup that the other players are not shown at all (the choices that were made and taken back, EXP-ORG-14): what each
 * player ends up with is told by one event (`setup_done`) when everybody has locked in. The place in the log stays, so that its numbers do not change. */
const HIDDEN_SETUP_MOVES = new Set(["choose_org", "choose_quick", "setup_tuck", "setup_untuck"]);

/** The locks of the setup: the players see who has locked in (EXP-ORG-14), the observers see nothing of the setup until everybody has locked in. */
const SETUP_LOCKS = new Set(["setup_lock", "setup_unlock"]);
/** The events that tell what everybody ended up with: only the last lock of a step has them. */
const SETUP_REVEALS = new Set(["organization", "setup_done"]);

/** The card drawn from the deck is told to the player who drew it only. */
export function publicEntry(e: LogEntry, viewer: number | null = null): PublicEntry {
  const type = String((e.action as Record<string, unknown>).type);
  const hidden: PublicEntry = { seq: e.seq, seat: e.seat, action: { type: "setup_hidden" }, events: [] };
  if (HIDDEN_SETUP_MOVES.has(type) && e.seat !== viewer) return hidden;
  // an observer (nobody's seat) is shown the setup when everybody has locked in: the last lock of a step carries the final choices
  if (SETUP_LOCKS.has(type) && viewer === null && !e.events.some((ev) => SETUP_REVEALS.has(String(ev.type)))) return hidden;
  const action = HIDDEN_CARD_ACTIONS.has(type)
    ? without(e.action as Record<string, unknown>, "card")
    : SECRET_CHOICES.has(type) && e.seat !== viewer
      ? without(without(e.action as Record<string, unknown>, "org"), "cards")
      : e.action;
  const events = e.events.map((ev) =>
    HIDDEN_CARD_EVENTS.has(String(ev.type)) || (ev.type === "draw_card" && ev.player !== viewer) ? without(ev, "card") : ev,
  );
  return { seq: e.seq, seat: e.seat, action: action as Record<string, unknown>, events };
}
