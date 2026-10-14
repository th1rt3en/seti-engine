// Words for the legal moves the engine offers. The UI offers only these moves (decision D10); it never works out a rule itself.
import cards from "../generated/cards.json";

export type Move = { type: string } & Record<string, unknown>;

type CardInfo = { name: string; cost: number; income: string | null; sector: string | null; free?: [string, number][] };
const CARDS = cards as unknown as Record<string, CardInfo>;

export function cardName(id: unknown): string {
  const c = CARDS[String(id)];
  return c ? `${c.name} (${String(id)})` : String(id);
}

const cap = (s: unknown): string => {
  const t = String(s);
  return t.charAt(0).toUpperCase() + t.slice(1);
};
const rewardList = (list: unknown): string =>
  (Array.isArray(list) ? (list as { t: string; n: number }[]) : [])
    .map((r) => `${r.n} ${r.t.replace("alien_card", "alien card").replace("vp", "VP").replace("trace", "trace of any color")}`)
    .join(" + ");
const planet = (s: unknown): string => cap(s);
const source = (s: unknown): string => {
  const t = String(s);
  return t === "deck" ? "the top of the deck" : t.startsWith("row:") ? `card ${Number(t.slice(4)) + 1} of the card row` : t;
};
const space = (m: Move): string => {
  const where =
    m.space === "overflow"
      ? "an overflow space"
      : m.space === "discovery"
        ? "a discovery space"
        : m.space === "sample"
          ? "a sample space"
          : `space ${Number(m.index) + 1} of the species board`;
  return `${where} (${m.color ?? "any"}) of the ${Number(m.slot) === 0 ? "left" : "right"} species`;
};

type Label = (m: Move) => string;

/** One entry per kind of move. A test checks that every kind the engine offered in random games has an entry. */
export const LABELS: Record<string, Label> = {
  launch: () => "Launch a probe (2 credits)",
  pass: () => "Pass",
  undo: () => "Undo the last move",
  end_turn: () => "End the turn",
  move_energy: () => "Spend 1 energy for 1 movement",
  move_probe: (m) => `Move probe ${String(m.probe)} to ring ${(m.to as number[])[0]}, sector ${(m.to as number[])[1]}`,
  buy_card: (m) => `Buy ${source(m.source)} (3 publicity)`,
  exchange: (m) => `Exchange 2 ${String(m.give)} for 1 ${String(m.get)}`,
  discard_free: (m) => `Discard ${cardName(m.card)} for its free action`,
  place_data: () => "Place 1 data in the computer",
  data_done: () => "Take the data (any extra is lost)",
  resolve_sector: (m) => `Resolve sector ${Number(m.sector)} next`,
  place_lower: (m) => `Place 1 data under computer tech ${Number(m.slot) + 1}`,
  tuck: (m) => `Tuck ${cardName(m.card)} for income`,
  skip_tuck: () => "Do not tuck a card",
  discard: (m) => `Discard ${cardName(m.card)}`,
  take_round_card: (m) => `Take ${cardName(m.card)} from the end-of-round cards`,
  choose_gold: (m) => `Mark the ${String(m.tile)} gold scoring tile`,
  orbit: (m) => `Orbit ${m.at === "pluto" ? "Pluto " : ""}with probe ${String(m.probe)} (1 credit, 1 energy)`,
  land: (m) => `Land ${m.at === "pluto" ? "on Pluto " : ""}with probe ${String(m.probe)}${m.moon ? ` on ${String(m.moon)}` : ""}`,
  land_free: (m) => `Land with probe ${String(m.probe)}${m.moon ? ` on ${String(m.moon)}` : ""} for free`,
  orbit_free: (m) => `Orbit with probe ${String(m.probe)} for free`,
  scan: () => "Scan (1 credit, 2 energy)",
  scan_earth: (m) => `Mark a signal in sector ${Number(m.sector)} (Earth's sector or next to it)`,
  scan_discard: (m) => `Discard ${source(m.source)} for a signal`,
  scan_hand_discard: (m) => `Discard ${cardName(m.card)} from your hand for a signal`,
  scan_mercury: () => "Pay 1 publicity for a signal in Mercury's sector",
  scan_probe: (m) => (m.mode === "launch" ? "Pay 1 energy to launch a probe" : "Pay 1 energy for 1 movement"),
  scan_done: () => "Finish the scan",
  research: (m) => `Research the tech in stack ${Number(m.stack) + 1} (6 publicity)`,
  take_tech: (m) => `Take the tech in stack ${Number(m.stack) + 1}`,
  place_computer_tech: (m) => `Put the tech in computer slot ${Number(m.slot) + 1}`,
  analyze: () => "Analyze data (1 energy)",
  play_card: (m) => `Play ${cardName(m.card)}`,
  complete_mission: (m) => `Complete the mission ${cardName(m.card)}`,
  deliver_sample: (m) => `Deliver capsule ${String(m.capsule)} for ${cardName(m.card)}`,
  cover: (m) => `Cover circle ${Number(m.circle) + 1} of ${cardName(m.card)}`,
  decline_cover: () => "Do not cover a circle",
  mark_signal: (m) => `Mark a signal in sector ${Number(m.sector)}`,
  signal_where: (m) => (m.where === "tile" ? "Mark the signal on the 'Oumuamua tile" : "Mark the signal in the sector"),
  place_trace: (m) => `Mark a trace on ${space(m)}`,
  take_card: (m) => `Take ${source(m.source)}`,
  pick_probe: (m) => `Choose probe ${String(m.probe)}`,
  gop: (m) => `Mark a signal in the sector of probe ${String(m.probe)}`,
  gop_done: () => "Stop choosing probes",
  row_pick: (m) => `Discard ${source(m.source)} for a signal`,
  hand_signal: (m) => `Discard ${cardName(m.card)} for a signal`,
  hand_signal_done: () => "Stop discarding cards",
  slingshot_pick: (m) => (m.choice === "move" ? "Gain 1 movement instead of publicity" : "Gain the publicity"),
  choose_land_slot: (m) => `Take first-lander space ${Number(m.slot) + 1}`,
  take_alien: (m) => `Take the ${m.source === "face_up" ? "face-up" : "top"} alien card`,
  choose_message: (m) => `Cover reward ${Number(m.hex) + 1} (${rewardList(m.reward)}) with your message tile`,
  play_exertian: () => "Play an Exertian card face down",
  skip_exertian: () => "Do not play an Exertian card",
  pol_pick: (m) => `Choose ${cardName(m.card)}`,
  opt_yes: () => "Yes, do it",
  opt_no: () => "No, skip it",
  pick_sample: (m) => `Choose sample ${Number(m.sample) + 1} on ${planet(m.planet)}`,
  mark_objective: (m) => `Mark task ${Number(m.task) + 1} of the objective ${String(m.objective)}`,
  remove_orbiter: (m) => `Remove your orbiter at ${planet(m.planet)}${m.first ? " (the first space)" : ""}`,
  remove_lander: (m) => `Remove your lander ${m.moon ? `on ${String(m.moon)}` : `at ${planet(m.planet)}`}`,
};

export function describeMove(m: Move): string {
  const label = LABELS[m.type];
  return label ? label(m) : `${m.type} ${JSON.stringify(Object.fromEntries(Object.entries(m).filter(([k]) => k !== "type")))}`;
}

/** Group the moves for display: the free actions apart from the main actions and the answers to a decision. */
export const FREE_ACTION_TYPES = new Set([
  "move_energy",
  "move_probe",
  "buy_card",
  "exchange",
  "discard_free",
  "place_data",
  "place_lower",
  "complete_mission",
  "deliver_sample",
]);

export function groupMoves(moves: Move[], pending: boolean, answeringFree = false): { title: string; moves: Move[] }[] {
  if (pending) {
    // a free action may interrupt the decisions of the main action (FREE-00): its moves come after the answers, in a group of their own
    const isFree = (m: Move) => !answeringFree && FREE_ACTION_TYPES.has(m.type);
    const groups = [
      { title: "Your choice", moves: moves.filter((m) => !isFree(m) && m.type !== "undo") },
      { title: "Free actions", moves: moves.filter(isFree) },
      { title: "Undo", moves: moves.filter((m) => m.type === "undo") },
    ];
    return groups.filter((g) => g.moves.length > 0);
  }
  const main = new Set(["launch", "pass", "orbit", "land", "scan", "research", "analyze", "play_card"]);
  const end = new Set(["end_turn", "undo"]);
  const groups = [
    { title: "Main action", moves: moves.filter((m) => main.has(m.type)) },
    { title: "Free actions", moves: moves.filter((m) => !main.has(m.type) && !end.has(m.type)) },
    { title: "Turn", moves: moves.filter((m) => end.has(m.type)) },
  ];
  return groups.filter((g) => g.moves.length > 0);
}

/** Why a move cannot be taken back, in words for the confirmation (the engine marks such moves `irreversible`, UNDO-01). */
export function irreversibleText(m: Move): string {
  switch (m.type) {
    case "pass":
      return "Passing shows you the end-of-round cards, so it cannot be undone.";
    case "end_turn":
      return "Ending the turn may reveal an alien species, so it cannot be undone.";
    case "buy_card":
    case "exchange":
    case "take_card":
      return "Taking a card shows a card from the deck (a card of the display is replaced from the deck), so this cannot be undone.";
    case "scan_done":
      return "Finishing the scan refills the card row from the deck, so it cannot be undone.";
    default:
      return "This move shows something that is hidden (a card from the deck, a card, a tile or a species), so it cannot be undone.";
  }
}

/** The moves that name a card of the player's hand: the player picks the card in the hand, then confirms. */
export const HAND_MOVE_TYPES = new Set(["tuck", "discard", "discard_free", "play_card", "scan_hand_discard", "hand_signal"]);

export const isHandMove = (m: Move, hand: string[]): boolean => HAND_MOVE_TYPES.has(m.type) && hand.includes(String(m.card));

/** The two moves are the same (the order of the fields does not matter). */
export const sameMove = (a: Move, b: Move): boolean => {
  const key = (m: Move): string =>
    JSON.stringify(
      Object.keys(m)
        .sort()
        .map((k) => [k, m[k]]),
    );
  return key(a) === key(b);
};

const cardTitle = (id: unknown): string => CARDS[String(id)]?.name ?? String(id);
const plural = (n: number, word: string): string => `${n} ${word}${n === 1 ? "" : "s"}`;
const freeText = (free: [string, number][] | undefined): string =>
  free && free.length > 0 ? free.map(([k, n]) => `${n} ${k}`).join(", ") : "nothing";

/** What the bar asks when the player has picked a card for this move. */
export function handMoveText(m: Move): string {
  const info = CARDS[String(m.card)];
  const name = cardTitle(m.card);
  const sector = info?.sector ?? "any";
  switch (m.type) {
    case "tuck":
      return `Confirm tucking ${name} for ${info?.income ?? "no"} income?`;
    case "play_card":
      return info && info.cost > 0
        ? `Pay ${plural(info.cost, "credit")} to play ${name} as your main action?`
        : `Play ${name} as your main action? It costs nothing.`;
    case "discard_free":
      return `Discard ${name} for its free action (${freeText(info?.free)})?`;
    case "discard":
      return `Discard ${name}?`;
    case "scan_hand_discard":
      return `Discard ${name} from your hand to mark a signal in a ${sector} sector?`;
    case "hand_signal":
      return `Discard ${name} to mark a signal in a ${sector} sector?`;
    case "take_round_card":
      return `Confirm keeping ${name} from the end-of-round cards? The others go back.`;
    default:
      return describeMove(m);
  }
}

/** A move as a line of the log. The identity of a card that stays hidden is not in the move (the server leaves it out). */
export function logText(m: Move): string {
  switch (m.type) {
    case "tuck":
      return "tucked a card for income";
    case "take_round_card":
      return "took an end-of-round card";
    case "play_exertian":
      return "played an Exertian card face down";
    case "pol_pick":
      return "chose a card";
    case "undo":
      return "took back the last move";
    case "exchange":
      return m.give === "card"
        ? `traded ${(m.cards as string[]).map(cardTitle).join(" and ")} for ${m.get === "card" ? `a card from ${source(m.source)}` : `1 ${String(m.get)}`}`
        : `traded 2 ${String(m.give)} for ${m.get === "card" ? `a card from ${source(m.source)}` : `1 ${String(m.get)}`}`;
    default:
      return describeMove(m);
  }
}

/** The card's free action is movement only: it does nothing for a player without a probe on the map. */
export const freeIsOnlyMovement = (id: unknown): boolean => {
  const free = CARDS[String(id)]?.free ?? [];
  return free.length > 0 && free.every(([k]) => k === "move");
};

/** What the bar asks when the player has picked a card of the display or the deck to buy. */
export function buyText(source: unknown, row: string[]): string {
  const s = String(source);
  if (s === "deck") return "Buy the top card of the deck for 3 publicity?";
  const id = row[Number(s.slice(4))];
  return `Buy ${id === undefined ? "this card" : cardTitle(id)} for 3 publicity?`;
}

/** The hint that goes with the cards of the hand being selectable. */
export function handHint(types: Set<string>): string {
  const what: string[] = [];
  if (types.has("tuck")) what.push("tuck it for income");
  if (types.has("play_card")) what.push("play it as your main action");
  if (types.has("discard_free")) what.push("discard it for its free action");
  if (types.has("discard")) what.push("discard it");
  if (types.has("scan_hand_discard") || types.has("hand_signal")) what.push("discard it for a signal");
  return `Select a card in your hand to ${what.join(", or to ")}.`;
}
