// What the game is asking, in a sentence or two, for the "?" button of the context bar. Each text says what the player is to do and names the rule
// of the spec (docs/spec) that it comes from. It explains; the engine decides what is legal.
const DECISION_HELP: Record<string, string> = {
  setup_tuck:
    "Tuck one card from your hand under your income card. It gives its income resource now and again every round (SETUP-36, INCOME-01).",
  objective_task:
    "What you just did fits a task on more than one objective. A trigger marks only one task: click the one to mark in the objectives panel (SOLO-OBJ-04). When only one task fits, it is marked without a question.",
  helion_tuck: "Tuck a card from your hand for income, as the organization says (INCOME-01).",
  income_tuck:
    "Tuck a card for income: it goes under your income card and gives its resource now and every round. You may also skip it (FAQ-01).",
  discard_to_four: "You are passing with more than 4 cards in hand: discard down to 4 (PASS-02).",
  take_round_card: "After passing take one of the end-of-round cards: pick one in the panel and keep it: it joins your hand (PASS-04).",
  data_overflow:
    "Your data pool holds 6 at most. Place data from the pool in your computer first to make room, or take the new data and lose what does not fit (RES-01).",
  sector_order: "Several sectors are complete. Choose which one is resolved next (TURN-05).",
  gold_choice:
    "You reached a gold milestone: mark a gold scoring tile that you have not marked yet. The earlier you choose a tile, the more it scores (MILE-02, MILE-03).",
  signal: "Mark a signal in a sector of the color shown (SECTOR-01). Click one of the highlighted sectors.",
  trace:
    "Mark a life trace of the color shown: on a discovery space, on a space of a species that is already discovered, or on an overflow space, which is always possible and scores 3 (LIFE-01).",
  take_card: "Take a card from the card row or the top of the deck.",
  research_tech: "Take a tech tile from a stack that you do not have yet (TECHACT-07).",
  computer_slot: "Put the computer tech in one of the slots of your computer (TECH-20).",
  mission_trigger:
    "A mission with circles can be advanced by what you just did. Cover a circle, one at a time, or decline (CARD-12, CARD-14).",
  message_reward: "Cover one reward of the Centaurian board with your message tile and take it (ALIEN-CEN-04).",
  exertian_play: "You reached an Exertian milestone. Pay its cost to play one Exertian card face down, or do not (ALIEN-EXE-03).",
  breach: "Breach the security card of this color: it goes to your hand. You may decline (EXP-ARK-06).",
  organelle: "Take the bonus of one organelle in the section of the color shown, then it moves along the cell (EXP-AMO-04).",
  land_free: "Land for free with a probe that stands on a planet.",
  orbit_land_free: "Orbit or land for free with a probe that stands on a planet.",
  choose_org: "Choose your organization: its income, its starting resources and its special action are on its card (EXP-ORG-04).",
  choose_quick: "Choose your quick start cards: they set up your first marks and give a lower half (EXP-QS-01, EXP-QS-02).",
};

const TURN_HELP =
  "On your turn take exactly one main action: launch a probe, orbit, land, scan, analyze data, play a card, research a tech, or pass. Free actions (moving a probe, trading, placing data, discarding a card for its corner, completing a mission) can be taken before, during or after it. End the turn when you are done (TURN-01, TURN-02, TURN-04).";

/** The help for what the game waits for now: the text of the pending decision, or of the turn when there is none. */
export function helpFor(kind: string | undefined): string {
  return kind === undefined ? TURN_HELP : (DECISION_HELP[kind] ?? "The game asks you to answer with one of the highlighted choices.");
}
