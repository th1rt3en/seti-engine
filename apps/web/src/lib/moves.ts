// Words for the legal moves the engine offers. The UI offers only these moves (decision D10); it never works out a rule itself.
import cards from "../generated/cards.json";
import organizations from "../generated/organizations.json";
import quickStart from "../generated/quick-start.json";

export type Move = { type: string } & Record<string, unknown>;

type CardInfo = {
  name: string;
  cost: number;
  income: string | null;
  sector: string | null;
  species?: string | null;
  free?: [string, number][];
};
const CARDS = cards as unknown as Record<string, CardInfo>;

export function cardName(id: unknown): string {
  const c = CARDS[String(id)];
  if (c) return `${c.name} (${String(id)})`;
  return ORGS[String(id)]?.name ?? String(id); // the organizations are pictured like cards
}

const ORGS = organizations as unknown as Record<string, { name: string; number: number; abilities: Record<string, string> }>;
const QUICK = quickStart as unknown as Record<string, { marks: string; lower: { effect: string; n: number }[] }>;
export const ORG_NAMES: Record<string, string> = Object.fromEntries(Object.entries(ORGS).map(([id, o]) => [id, o.name]));
export const orgName = (id: unknown): string => ORGS[String(id)]?.name ?? String(id);
const quickText = (id: unknown): string => {
  const q = QUICK[String(id)];
  if (!q) return String(id);
  const gains = q.lower.map((e) => `${e.n} ${e.effect === "score" ? "VP" : e.effect.replace("_", " ")}`).join(", ");
  return `${String(id)}${q.marks ? `: mark ${q.marks}` : ""}${gains ? `; gain ${gains}` : ""}`;
};

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
  show_move: (m) => `Show ${cardName(m.card)} from your hand: gain 1 movement`,
  show_move_done: () => "Stop showing cards",
  show_energy: (m) => `Show ${cardName(m.card)} from your hand: gain 1 energy`,
  show_energy_done: () => "Stop showing cards",
  place_lower: (m) => `Place 1 data under computer tech ${Number(m.slot) + 1}`,
  tuck: (m) => `Tuck ${cardName(m.card)} for income`,
  skip_tuck: () => "Do not tuck a card",
  discard: (m) => `Discard ${cardName(m.card)}`,
  take_round_card: (m) => `Take ${cardName(m.card)} from the end-of-round cards`,
  setup_unlock: () => "Change my choices",
  setup_lock: () => "Lock in your choices: the others see them when everybody has locked in",
  choose_org: (m) =>
    `Take the organization ${orgName(m.org)}${ORGS[String(m.org)] ? ` (${ORGS[String(m.org)]?.abilities.passive ?? ORGS[String(m.org)]?.abilities.mainAction ?? ""})` : ""}`,
  setup_tuck: (m) => `Tuck ${cardName(m.card)} for income`,
  setup_untuck: (m) => `Take back the tuck of ${cardName(m.card)}`,
  choose_quick: (m) => `Keep the quick start cards ${((m.cards as string[]) ?? []).map(quickText).join(" and ")}`,
  org_free: (m) => orgFreeLabel(m),
  breach: () => "Breach your security card of that color (take it into your hand)",
  skip_breach: () => "Do not breach the security card",
  corner_pick: (m) => `Choose ${String(m.kind)}: gain it for each card in your hand with that icon in its free-action corner`,
  decipher: (m) =>
    `Place the ${String(m.glyph)} glyph token in the ${String(m.row)} row, slot ${Number(m.index) + 1}, and gain its resource`,
  glyph_group: (m) => `Gain the resources of glyph group ${Number(m.group) + 1}`,
  skip_organelle: (m) => `Skip: no ${String(m.color)} organelle is available`,
  pick_organelle: (m) => `Gain the bonus of the organelle on space ${String(m.space)}`,
  amoeba_remove: (m) => `Remove your marker from the ${String(m.color)} space ${Number(m.index) + 1} of the Amoeba board`,
  spend_credit: () => "Spend 1 credit for 2 VP and 2 publicity",
  spend_done: () => "Stop spending credits",
  hold_done: () => "Done moving: check the card now",
  restructure_card: (m) => `Discard ${cardName(m.card)} and gain its income resource`,
  restructure_done: () => "Stop discarding cards",
  return_mission: (m) => `Return the mission ${cardName(m.card)} to your hand`,
  discard_corner: (m) => `Discard ${cardName(m.card)} and gain its free-action corner 3 times`,
  discard_corner_none: () => "No card to discard",
  od_step: (m) => `Orbital Dynamics: move probe ${String(m.probe)} one step`,
  org_mark: (m) => `Mark the ${String(m.space).replace("_", " ")} reward space on your organization and gain it`,
  org_skip: () => "Do not mark a reward space",
  org_main: (m) =>
    m.org === "futurespan_institute"
      ? "Futurespan Institute: play the prepared card for free"
      : m.tile === "launch"
        ? "Xenolab: launch a probe (1 credit, flips the launch tile)"
        : m.tile === "scan"
          ? "Xenolab: scan (2 energy, flips the scan tile)"
          : `Xenolab: research the tech in stack ${Number(m.stack) + 1} (4 publicity, flips the research tile)`,
  scan_token: (m) => `Discard a signal token and ${source(m.source)} for a signal`,
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
  scan_probe: (m) => (m.mode === "launch" ? "Pay 1 energy to launch a probe" : "Gain 1 movement for free"),
  scan_skip: () => "Skip this step",
  scan_done: () => "Finish the scan",
  research: (m) => `Research the tech in stack ${Number(m.stack) + 1}`,
  take_tech: (m) => `Take the tech in stack ${Number(m.stack) + 1}`,
  place_computer_tech: (m) => `Put the tech in computer slot ${Number(m.slot) + 1}`,
  analyze: () => "Analyze (1 energy)",
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
  choose_land_slot: (m) => `Cover the first-lander space number ${Number(m.slot) + 1} of the planet`,
  take_alien: (m) => `Take the ${m.source === "face_up" ? "face-up" : "top"} alien card`,
  choose_message: (m) => `Cover reward ${Number(m.hex) + 1} (${rewardList(m.reward)}) with your message tile`,
  play_exertian: () => "Play an Exertian card face down",
  skip_exertian: () => "Do not play an Exertian card",
  skip_land: () => "Do not land",
  pol_pick: (m) => `Choose ${cardName(m.card)}`,
  opt_yes: () => "Yes, do it",
  opt_no: () => "No, skip it",
  pick_sample: (m) =>
    m.sample === undefined ? `Choose a sample on ${planet(m.planet)}` : `Choose sample ${Number(m.sample) + 1} on ${planet(m.planet)}`,
  mark_objective: (m) => `Mark task ${Number(m.task) + 1} of the objective ${String(m.objective)}`,
  remove_orbiter: (m) => `Remove your orbiter at ${planet(m.planet)}${m.first ? " (the first space)" : ""}`,
  remove_lander: (m) => `Remove your lander ${m.moon ? `on ${String(m.moon)}` : `at ${planet(m.planet)}`}`,
};

function orgFreeLabel(m: Move): string {
  const org = String(m.org);
  const name = orgName(org);
  if (org === "fenwick_research_center") return `${name}: spend 1 publicity for ${source(m.source)}, then gain its free-action corner`;
  if (org === "mission_relay") return `${name}: spend 2 publicity for ${source(m.source)}, then gain its income resource`;
  if (org === "stratus_core") return `${name}: gain the free-action corners of all cards in the card row`;
  if (org === "deep_sky_survey") return `${name}: switch ${cardName(m.card)} with card ${Number(m.row) + 1} of the card row`;
  if (org === "sentinel_probe_network") return `${name}: gain the free-action corner of the card you played`;
  if (org === "futurespan_institute")
    return m.delay ? `${name}: move the token 3 spaces farther and take ${source(m.source)}` : `${name}: Prepare (+${String(m.ahead)})`;
  if (org === "cosmos_strategy_group") return `${name}: gain ${source(m.source)} and clear your marked reward spaces`;
  if (org === "helion_assembly")
    return `${name}: destroy your ${String(m.tech)} tech, then tuck a card for income and clear your marked reward spaces`;
  if (org === "turing_systems") return `${name}: use the ${String(m.tech)} tech this turn`;
  return `${name}: use the once-per-round ability`;
}

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
  "org_free",
  "decipher",
  "od_step",
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
  const main = new Set(["launch", "pass", "orbit", "land", "scan", "research", "analyze", "play_card", "org_main"]);
  const end = new Set(["end_turn", "undo"]);
  const groups = [
    { title: "Main action", moves: moves.filter((m) => main.has(m.type)) },
    { title: "Free actions", moves: moves.filter((m) => !main.has(m.type) && !end.has(m.type)) },
    { title: "Turn", moves: moves.filter((m) => end.has(m.type)) },
  ];
  return groups.filter((g) => g.moves.length > 0);
}

/** A short sentence for the question before a move that cannot be taken back: what the move does, and what it shows. */
export function irreversibleText(m: Move): string {
  switch (m.type) {
    case "pass":
      return "Pass now? You will see the end-of-round cards.";
    case "end_turn":
      return "End your turn? A species may be revealed.";
    case "buy_card":
    case "exchange":
    case "take_card":
      return m.source === "deck" || m.get === "card"
        ? "Draw from the deck? You will see the card."
        : "Take this card? The display is refilled from the deck.";
    case "scan_done":
      return "Finish the scan? The card row is refilled from the deck.";
    default:
      return `${describeMove(m)}? It shows something hidden.`;
  }
}

/** The moves that name a card of the player's hand: the player picks the card in the hand, then confirms. */
export const HAND_MOVE_TYPES = new Set([
  "tuck",
  "discard",
  "discard_free",
  "play_card",
  "scan_hand_discard",
  "hand_signal",
  "restructure_card", // Turing Systems restructuring: the cards to discard are picked in the hand
  "discard_corner", // Sentinel Probe Network
  "show_move", // #74 Pre-launch Testing: the cards to show are picked in the hand
  "show_energy", // #90 Fuel Tanks Construction: the cards with an energy income to show are picked in the hand
  "org_free", // Futurespan, Deep Sky Survey, Helion Assembly: the card is picked in the hand
]);

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

const cardTitle = (id: unknown): string => CARDS[String(id)]?.name ?? ORGS[String(id)]?.name ?? String(id);
const plural = (n: number, word: string): string => `${n} ${word}${n === 1 ? "" : "s"}`;
const FREE_WORDS: Record<string, string> = {
  score: "points",
  move: "movement",
  explore_minor: "minor exploration reward (reveal the next exploration card)",
};
/** The free-action corner and the income resource of a card, in words (the panel of #ET.15 shows them on its buttons). */
export const cornerWords = (id: string): string => freeText(CARDS[id]?.free as [string, number][] | undefined);
export const incomeWords = (id: string): string => CARDS[id]?.income ?? "nothing";
const freeText = (free: [string, number][] | undefined): string =>
  free && free.length > 0 ? free.map(([k, n]) => `${n} ${FREE_WORDS[k] ?? k}`).join(", ") : "nothing";

const REWARD_WORDS: Record<string, [string, string]> = {
  credit: ["credit", "credits"],
  energy: ["energy", "energy"],
  data: ["data", "data"],
  publicity: ["publicity", "publicity"],
  vp: ["point", "points"],
  card_random: ["random card", "random cards"],
  signal_token: ["signal token", "signal tokens"],
};

/** "1 credit", "3 points": a reward in words. */
export const rewardWords = (r: { t: string; n: number }): string => {
  const w = REWARD_WORDS[r.t];
  return `${r.n} ${w ? (r.n === 1 ? w[0] : w[1]) : r.t}`;
};

/** The facts of a card the buttons over it need: its cost and what it is paid with (the Centaurian cards cost energy, the others credits). */
export const cardInfo = (id: unknown): { cost: number; pays_energy: boolean; income: string | null } | undefined => {
  const c = CARDS[String(id)];
  return c ? { cost: c.cost, pays_energy: c.species === "centaurians", income: c.income } : undefined;
};

/** The color of the sector a card marks a signal in ("any" for a card with no sector). */
export const cardSector = (id: unknown): string => CARDS[String(id)]?.sector ?? "any";

/** The glyph of the free corner of a card, if it has one (a Glyphids card: its corner is a glyph icon). */
export const cornerGlyph = (id: unknown): string | null => {
  const k = CARDS[String(id)]?.free?.[0]?.[0];
  return typeof k === "string" && k.startsWith("glyph:") ? k.slice(6) : null;
};

/** What the bar asks when the player has picked a card for this move. `glyph` is what the glyph icon of a Glyphids card's corner gives now: the
 * reward of its slot, or null while that glyph has not been placed on the translation board. */
export function handMoveText(m: Move, glyph?: { reward: { t: string; n: number } | null }): string {
  const info = CARDS[String(m.card)];
  const name = cardTitle(m.type === "choose_org" ? m.org : m.card);
  const sector = info?.sector ?? "any";
  switch (m.type) {
    case "tuck":
      return `Confirm tucking ${name} for ${info?.income ?? "no"} income?`;
    case "play_card":
      return info && info.cost > 0
        ? `Pay ${plural(info.cost, "credit")} to play ${name} as your main action?`
        : `Play ${name} as your main action? It costs nothing.`;
    case "discard_free": {
      const g = cornerGlyph(m.card);
      if (g !== null && glyph !== undefined)
        return glyph.reward
          ? `Discard ${name} for its free action: the ${g} glyph gives ${rewardWords(glyph.reward)}?`
          : `Discard ${name} for its free action? The ${g} glyph is not on the translation board, so you gain nothing.`;
      return `Discard ${name} for its free action (${freeText(info?.free)})?`;
    }
    case "discard":
      return `Discard ${name}?`;
    case "scan_hand_discard":
      return `Discard ${name} from your hand to mark a signal in a ${sector} sector?`;
    case "hand_signal":
      return `Discard ${name} to mark a signal in a ${sector} sector?`;
    case "take_round_card":
      return `Confirm keeping ${name} from the end-of-round cards? The others go back.`;
    case "show_move":
      return `Show ${name} to everybody and gain 1 movement? The card stays in your hand.`;
    case "show_energy":
      return `Show ${name} to everybody and gain 1 energy? The card stays in your hand.`;
    case "choose_org":
      return `Take the organization ${name}? The other one goes back to the box.`;
    case "choose_quick":
      return `Keep the quick start cards ${((m.cards as string[]) ?? []).map(quickText).join(" and ")}?`;
    default:
      return describeMove(m);
  }
}

/** A move as a line of the log. The identity of a card that stays hidden is not in the move (the server leaves it out). */
export function logText(m: Move): string {
  switch (m.type) {
    case "choose_org":
      return "chose an organization"; // what it is stays secret until everybody has locked in (EXP-ORG-14); the log names it then
    case "choose_quick":
      return "chose the quick start cards";
    case "setup_tuck":
      return "tucked a card for income";
    case "setup_untuck":
      return "took a tuck back";
    case "setup_lock":
      return "locked in their choices";
    case "setup_unlock":
      return "unlocked their choices to change them";
    case "tuck":
      return "tucked a card for income";
    case "take_round_card":
      return "took an end-of-round card";
    case "play_exertian":
      return "played an Exertian card face down";
    case "pol_pick":
      return "chose a drawn card";
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
/** What the bar asks when the player has clicked a card of the display (or the deck) for one of the moves that name it. */
export function rowMoveText(m: Move, row: string[]): string {
  const s = String(m.source);
  const id = s === "deck" ? undefined : row[Number(s.slice(4))];
  const card = s === "deck" ? "the top card of the deck" : id === undefined ? "this card" : cardTitle(id);
  switch (m.type) {
    case "buy_card":
      return buyText(m.source, row);
    case "take_card":
      return `Take ${card}?`;
    case "row_pick":
    case "scan_discard":
      return `Discard ${card} for a signal?`;
    case "scan_token":
      return `Discard a signal token and ${card} for a signal?`;
    default:
      return describeMove(m);
  }
}

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
