// Words for the legal moves the engine offers. The UI offers only these moves (decision D10); it never works out a rule itself.
import cards from "../generated/cards.json";

export type Move = { type: string } & Record<string, unknown>;

type CardInfo = { name: string; cost: number; income: string | null; sector: string | null };
const CARDS = cards as Record<string, CardInfo>;

export function cardName(id: unknown): string {
  const c = CARDS[String(id)];
  return c ? `${c.name} (${String(id)})` : String(id);
}

const cap = (s: unknown): string => {
  const t = String(s);
  return t.charAt(0).toUpperCase() + t.slice(1);
};
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
  orbit: (m) => `Orbit with probe ${String(m.probe)} (1 credit, 1 energy)`,
  land: (m) => `Land with probe ${String(m.probe)}${m.moon ? ` on ${String(m.moon)}` : ""}`,
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
  choose_message: (m) => `Cover reward ${Number(m.hex) + 1} with your message tile`,
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
export function groupMoves(moves: Move[], pending: boolean): { title: string; moves: Move[] }[] {
  if (pending) return [{ title: "Your choice", moves }];
  const main = new Set(["launch", "pass", "orbit", "land", "scan", "research", "analyze", "play_card"]);
  const end = new Set(["end_turn"]);
  const groups = [
    { title: "Main action", moves: moves.filter((m) => main.has(m.type)) },
    { title: "Free actions", moves: moves.filter((m) => !main.has(m.type) && !end.has(m.type)) },
    { title: "Turn", moves: moves.filter((m) => end.has(m.type)) },
  ];
  return groups.filter((g) => g.moves.length > 0);
}
