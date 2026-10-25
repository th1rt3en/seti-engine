// A game as one viewer sees it: a bar on top with the round, the turn, what the game is waiting for and the moves to choose from; the card row
// and the alien species on the left; the board in the middle; the publicity track and the tech stacks to its right; the tracker of all players
// floating at the right edge; the hand floating in the bottom left corner. The live game and the replay both use it. It works out no rule:
// everything comes from the engine's view.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { LastMove } from "@/lib/lastMove";
import { type DecisionSource, sourceLabel } from "@/lib/sources";
import { firstRoundOrder, ordinal, turnOrder } from "@/lib/turnOrder";
import type { View } from "@seti/protocol";
import type { CSSProperties, ReactNode } from "react";
import { ArkhosPanel } from "./ArkhosPanel";
import { BarFold } from "./BarFold";
import { BarHeight } from "./BarHeight";
import { type BoardInteraction, type BoardSpots, BoardView, type GoldChoice } from "./BoardView";
import { ChipName } from "./ChipName";
import { GlyphidsPanel } from "./GlyphidsPanel";
import { ExertianDock, HandDock, type HandSelection } from "./HandDock";
import { Hint } from "./Hint";
import {
  CreditIcon,
  DataIcon,
  DeckCardIcon,
  EnergyIcon,
  ExofossilIcon,
  LongTermIcon,
  MoveIcon,
  ObjectiveIcon,
  ProgressIcon,
  PublicityIcon,
  RivalCardBack,
  ScoreIcon,
  SignalTokenIcon,
  TechKindIcon,
} from "./Icons";
import { MissionsPanel } from "./MissionsPanel";
import { OrgName } from "./OrgName";
import { OrgPanel } from "./OrgPanel";
import { PlayerTracker } from "./PlayerTracker";
import { PublicitySlot } from "./PublicitySlot";
import { RoundPiles } from "./RoundPiles";
import { RowDock, type RowSelection } from "./RowDock";
import { SoloPanel, objectiveFacts, progressSpace } from "./SoloPanel";
import { type TechPick, TechStacks } from "./TechStacks";
import { TrackerDock } from "./TrackerDock";

/** The publicity track ends at 10 (RES-02). */
const PUBLICITY_MAX = 10;
const ROUNDS = 5;

/** What the engine waits for, in words. */
const DECISION: Record<string, string> = {
  setup_tuck: "Tuck a card for income",
  helion_tuck: "Tuck a card for income",
  setup_start: "Setting up the game",
  breach: "Choose whether to breach a security card",
  income_tuck: "Tuck a card for income, or skip",
  discard_to_four: "Discard down to four cards",
  take_round_card: "Take an end-of-round card",
  data_overflow: "Place data first, or take the data",
  sector_order: "Choose which completed sector to resolve next",
  gold_choice: "Mark a gold scoring tile",
  signal: "Mark a signal",
  trace: "Mark a trace",
  scan_step: "Scan",
  take_card: "Take a card",
  oumuamua_signal: "Mark a signal",
  show_energy: "Choose a card from your hand to show",
  show_move: "Choose a card from your hand to show",
  pol_corner: "Discard for free action corner",
  pol_income: "Discard for income corner",
  land_free: "Land for free",
  orbit_land_free: "Orbit or land for free",
  land_data_slot: "Choose a landing space to cover",
  message_reward: "Choose a Centaurian milestone reward",
  exertian_play: "Play an Exertian card?",
  research_tech: "Research a tech",
  computer_slot: "Choose a computer slot",
  pick_probe: "Pick a probe",
  objective_task: "Choose an objective task to complete",
  amoeba_remove: "Remove one of your markers on the Amoeba board",
  choose_org: "Choose an organization",
  choose_quick: "Choose 2 quickstart cards to keep",
  corner_pick: "Choose {publicity}, {data} or 1 {move}",
  discard_corner: "Discard a non-alien card to gain x3 its free corner effect",
  glyph_group: "Choose a glyph group",
  hold: "Use your movement, or continue",
  mascamite_sample: "Choose a sample token to gain its reward",
  mission_trigger: "Choose a mission reward",
  optional: "Spend an {exofossil} for extra effect?",
  org_mark: "Mark a reward space of your organization board, or skip",
  remove_lander: "Choose a lander to remove",
  remove_orbiter: "Choose an orbiter to remove",
  restructure: "Choose any number of cards to discard",
  return_mission: "Choose an incomplete mission",
  slingshot: "Gain movement instead of publicity",
  take_alien_card: "Take an alien card",
};

const capital = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1);
const humanize = (kind: string): string => DECISION[kind] ?? capital(kind.replace(/_/g, " "));

const PROMPT_ICONS: Record<string, ReactNode> = {
  publicity: <PublicityIcon size={20} />,
  data: <DataIcon size={20} />,
  move: <MoveIcon size={20} />,
  energy: <EnergyIcon size={20} />,
  exofossil: <ExofossilIcon size={20} />,
};
/** The text of the context bar, with the icons that it names in braces: "Spend an {exofossil} for extra effect?". */
function withIcons(text: string): ReactNode {
  return text.split(/(\{[a-z]+\})/).map((part, i) => {
    const icon = PROMPT_ICONS[part.slice(1, -1)];
    return icon && part.startsWith("{") ? <span key={`${i}-${part}`}>{icon}</span> : part;
  });
}

/** What a player who is not the one to act reads: "Alice must choose a card" (a question is "must answer: ..."). */
const mustText = (text: string): string =>
  text.endsWith("?") ? `must answer: ${text}` : `must ${text.charAt(0).toLowerCase()}${text.slice(1)}`;

/** What the engine waits for, with the counts that it keeps for some decisions ("2/3"). */
function decisionText(kind: string, data: Record<string, unknown> | undefined): string {
  const left = Number(data?.left);
  const of = Number(data?.of);
  if (kind === "gop" && left > 0) return `Choose up to ${left} probe${left === 1 ? "" : "s"}`;
  if (kind === "hand_signal") return `Discard a card from your hand to mark a signal${of > 1 ? ` (${of - left + 1}/${of})` : ""}`;
  if (kind === "row_pick") {
    const idx = Number(data?.idx);
    return `Discard a card from the display for a signal${of > 1 ? ` (${idx}/${of})` : ""}`;
  }
  return humanize(kind);
}

/** The steps of the scan that the player can do now, from the moves the engine offers (any order: they are all offered at once). */
function scanStepText(types: Set<string>): string {
  const steps: string[] = [];
  if (types.has("scan_earth")) steps.push("Signal at Earth");
  if (types.has("scan_discard")) steps.push("Signal from display");
  if (types.has("scan_token")) steps.push("Signal token and display card for a signal");
  if (types.has("scan_mercury")) steps.push("Spend 1 publicity to signal at Mercury");
  if (types.has("scan_hand_discard")) steps.push("Signal from hand");
  if (types.has("scan_probe")) steps.push("Launch (1 {energy}) / 1 {move}");
  if (steps.length === 0) return "Scan: no step is left, finish the scan";
  const done = types.has("scan_done") ? ", or finish the scan" : "";
  return `Choose in any order: ${steps.join(", ")}${done}`;
}

/** Who has locked in their choices of the organization and the quick start cards, and who is still choosing (EXP-ORG-14). */
export function stillChoosing(view: View, names: string[]): string[] {
  const name = (i: number): string => names[i] ?? `Player ${i + 1}`;
  return view.state.players
    .filter((p) => !(view.state.rival && p.index === view.state.rival.index) && !p.setup_locked)
    .map((p) => name(p.index));
}

export function setupStatus(view: View, names: string[]): string {
  const name = (i: number): string => names[i] ?? `Player ${i + 1}`;
  const players = view.state.players.filter((p) => !(view.state.rival && p.index === view.state.rival.index));
  const done = players.filter((p) => p.setup_locked).map((p) => name(p.index));
  const open = players.filter((p) => !p.setup_locked).map((p) => name(p.index));
  return `Locked in: ${done.length > 0 ? done.join(", ") : "nobody yet"}. Still choosing: ${open.join(", ")}.`;
}

export function promptOf(view: View, names: string[]): { who: string; mine: boolean; text: string } {
  const s = view.state;
  if (s.phase !== "finished" && s.pending[0]?.kind === "setup_choice") {
    // everybody chooses at the same time (EXP-ORG-14)
    const mine = view.viewer !== null && (view.acting ?? []).includes(view.viewer);
    return {
      who: "",
      mine,
      text: mine
        ? view.legal.some((m) => m.type === "setup_tuck" || m.type === "setup_untuck")
          ? "Tuck your cards for income, one at a time, then lock in"
          : "Choose an organization and 2 quickstart cards"
        : `Waiting for other players. Still choosing: ${stillChoosing(view, names).join(", ")}`,
    };
  }
  const actor = view.to_act;
  if (s.phase === "finished") return { who: "", mine: false, text: "Game over" };
  if (actor === null) return { who: "", mine: false, text: "Starting..." };
  const mine = view.viewer !== null && actor === view.viewer;
  const who = s.rival && actor === s.rival.index ? "Rival" : (names[actor] ?? `Player ${actor + 1}`);
  const decision = s.pending[0];
  if (mine) {
    if (decision?.kind === "scan_step") return { who, mine, text: scanStepText(new Set(view.legal.map((m) => String(m.type)))) };
    if (decision?.kind === "organelle") {
      const color = String(decision.data?.color);
      const none = view.legal.some((m) => m.type === "skip_organelle");
      return {
        who,
        mine,
        text: none ? `No ${color} organelle token is available: skip` : `Choose an organelle token of the ${color} section`,
      };
    }
    if (decision) return { who, mine, text: decisionText(decision.kind, decision.data) };
    return { who, mine, text: s.main_done ? "Take free actions, or end the turn" : "Choose a main action" };
  }
  return { who, mine, text: decision ? mustText(decisionText(decision.kind, decision.data)) : "is taking a turn" };
}

/** The techs that the rival stores are named after their kind and their glyph ("probe-dot", "computer-link", SOLO-18). */
const TECH_KINDS = [
  { prefix: "probe", name: "probe" },
  { prefix: "telescope", name: "telescope" },
  { prefix: "computer", name: "computer" },
] as const;

/** What the rival of a solo game has, in the cells of its pill (they are under the resources of the other pills): the data on its computer, the actions it has
 * played this round and the cards it has left, its place on the progress track, the objectives that you have completed against those that you must spend,
 * and the techs that it stores by kind. Everything is in the view of the engine; nothing is worked out here. */
function RivalCells({ view }: { view: View }) {
  const r = view.state.rival;
  if (!r) return null;
  const f = objectiveFacts(view);
  const kinds = TECH_KINDS.map((k) => ({ ...k, n: r.techs.filter((t) => t.startsWith(`${k.prefix}-`)).length }));
  return (
    <span className="rivalcells">
      <span className="res" title="The rival's publicity (0 to 10)">
        <PublicityIcon size={18} />
        <b>{view.state.players[r.index]?.publicity ?? 0}/10</b>
      </span>
      <span className="res" title="Data on the rival's computer (0 to 6)">
        <DataIcon size={18} />
        <b>{r.computer}/6</b>
      </span>
      <span
        className="res"
        title="Actions: the cards the rival has played this round, and the cards left in its deck. When none is left it passes."
      >
        <RivalCardBack used height={20} />
        <b>{r.used.length}</b>
        <RivalCardBack height={20} />
        <b>{r.deck.length}</b>
      </span>
      <span
        className="res"
        title="The rival's marker on the 12 spaces of its progress track. Each time it goes round the track (back to the start), the rival gains an advanced action card."
      >
        <ProgressIcon size={18} />
        <b>{progressSpace(view) ?? r.progress + 1}/12</b>
        <span className="muted small" title="Advanced action cards the rival has gained">
          +{r.advanced.length}
        </span>
      </span>
      {f ? (
        <span
          className="res"
          title={
            f.round <= 4
              ? `Completed objectives: at the end of round ${f.round}, before income, you spend ${f.round} of them (1, 2, 3 and 4 after rounds 1 to 4). For each one that you cannot spend, the rival advances 3 spaces on its progress track.`
              : "Completed objectives: nothing is spent after round 5. Every objective that is not completed gives the rival 5 points."
          }
        >
          <ObjectiveIcon size={18} />
          <b>
            {f.unspent}
            {f.round <= 4 ? `/${f.round}` : ""}
          </b>
        </span>
      ) : null}
      {f && f.longTerm > 0 ? (
        <span
          className="res"
          title={`Long-term objectives: ${f.openLongTerm} circle${f.openLongTerm === 1 ? "" : "s"} still open. At the end of rounds 2, 3 and 4 the rival advances one space for each open task.`}
        >
          <LongTermIcon size={18} />
          <b>{f.openLongTerm}</b>
        </span>
      ) : null}
      <span className="res" title={`The techs the rival stores: ${kinds.map((k) => `${k.n} ${k.name}`).join(", ")}`}>
        {kinds.map((k) => (
          <span key={k.prefix} title={`${k.name} techs`}>
            <TechKindIcon kind={k.name} size={18} />
            <b>{k.n}</b>
          </span>
        ))}
      </span>
    </span>
  );
}

export function GameView({
  view,
  names,
  moves,
  topExtra,
  aboveMoves,
  previous,
  hand,
  row,
  tech,
  log,
  chat,
  results,
  overlay,
  context,
  rowFlash,
  contextActions,
  hint,
  interaction,
  lastMove,
  spots,
  goldChoice,
}: {
  view: View;
  names: string[];
  /** The view before this one, to show what has just happened. */
  previous?: View | null;
  /** Picking cards of the hand for the moves of the bar. */
  hand?: HandSelection;
  /** Picking a card of the card row, or the top of the deck. */
  row?: RowSelection;
  /** Picking a tech from the stacks. */
  tech?: TechPick;
  /** The log of the moves (the live game shows it). */
  log?: ReactNode;
  /** The chat of the table (the live game shows it): a panel to the left of the log. */
  chat?: ReactNode;
  /** The results of a game that is over, in a panel of their own under the bar and over the board (the page can hide it). */
  results?: ReactNode;
  /** A panel over the page (the player boards). */
  overlay?: ReactNode;
  /** What the context bar asks at the moment (a choice made on the board): it replaces the prompt of the game. */
  context?: ReactNode;
  /** The card row blinks to show where a card is to be picked up (after a trade for a card). */
  rowFlash?: boolean;
  /** Buttons for the answers that are no choice on the board (skip, yes, no ...): in the context bar under its question. */
  contextActions?: ReactNode;
  /** The reminder of what can be done now, behind a small ? button next to the question. */
  hint?: ReactNode;
  /** Picking a probe and a space to move it to. */
  interaction?: BoardInteraction;
  /** Where the last move left its mark on the board. */
  lastMove?: LastMove | null;
  /** Places on the board that a move can be made at (landing, orbiting, signals, traces). */
  spots?: BoardSpots;
  /** Marking a gold scoring tile. */
  goldChoice?: GoldChoice;
  /** The moves of the player to act (and the buttons that go with them): shown in the bar on top. */
  moves?: ReactNode;
  /** Connection and clock information for the bar. */
  topExtra?: ReactNode;
  /** A bar above the move bar (a proposal of another player that waits for an answer). */
  aboveMoves?: ReactNode;
}) {
  const s = view.state;
  // when the game is over the score is the final one (the board, the end-of-game cards, the gold tiles, the Exertian cards, the danger loss)
  const finalTotal = (player: number): number | undefined =>
    s.phase === "finished" ? (s.final_scores as { player?: number; total?: number }[]).find((f) => f.player === player)?.total : undefined;
  // exofossils exist once 'Oumuamua is face up: they show with the other resources (ALIEN-OUM-02)
  const oumuamua = s.species.some((sp) => sp.discovered && sp.species === "oumuamua");
  const prompt = promptOf(view, names);
  // which one of how many cards to tuck for income it is, when there are several in a row: "(1/3)"
  const tuckOf = s.pending[0]?.data as { number?: number; of?: number } | undefined;
  const tuckCount =
    (s.pending[0]?.kind === "setup_tuck" || s.pending[0]?.kind === "income_tuck") &&
    tuckOf?.of !== undefined &&
    tuckOf.of > 1 &&
    tuckOf.number
      ? `${tuckOf.number}/${tuckOf.of}`
      : "";
  // what caused the decision that is asked now, at the end of the bar: "(Helion Assembly)"
  const cause = sourceLabel(
    s.pending[0]?.source as DecisionSource | null | undefined,
    s.sectors.map((sec) => sec.star),
    s.species.map((sp, i) => (sp.discovered ? sp.species.charAt(0).toUpperCase() + sp.species.slice(1) : `Species ${i + 1}`)),
  );
  const actor = view.to_act === null ? undefined : s.players[view.to_act];
  // the order of play of this round (the marker of the starting player moves one seat on at every round, so it is worked out from every view)
  const order = turnOrder(s.players, s.start_player);
  // the pills keep the order of the first round all game long
  const pills = firstRoundOrder(s.players, s.start_player, s.round);
  return (
    <div className="game">
      <header className="topbar" aria-label="Round, turn, current player and moves">
        <div className="toprow">
          <BarFold />
          <div className="counter">
            <span className="label">Round</span>
            <span className="big">
              {Math.min(s.round, ROUNDS)}
              <small>/{ROUNDS}</small>
            </span>
          </div>
          <div className="counter">
            <span className="label">Turn</span>
            <span className="big">{s.turn}</span>
          </div>
          <div className={prompt.mine ? "now mine" : "now"} aria-live="polite">
            {actor ? <span className="dot big" style={{ background: PLAYER_COLOR[actor.color] ?? "#fff" }} /> : null}
            <div className="nowtext">
              <div className="nowline">
                <b className="who" style={actor ? { color: PLAYER_COLOR[actor.color] } : undefined}>
                  {prompt.who ? `${prompt.who}${prompt.mine ? " (you)" : ""}${prompt.mine || context ? ":" : ""}` : " "}
                </b>
                <span className={context ? "prompt asking" : "prompt"}>
                  {context ?? withIcons(prompt.text)}
                  {cause && view.state.pending.length > 0 ? ` (${cause})` : ""}
                  {tuckCount ? ` (${tuckCount})` : ""}
                </span>
              </div>
              {contextActions ? <div className="contextactions">{contextActions}</div> : null}
            </div>
            {hint ? <Hint>{hint}</Hint> : null}
          </div>
          <ul
            className="scorechips"
            aria-label="The players, in the order of play of the first round"
            // every pill has the same cells, so the resources of the players line up whatever the length of a name (a grid with a column for each cell)
            style={{ "--cols": 10 + (s.options.expansion ? 1 : 0) + (oumuamua ? 1 : 0) } as CSSProperties}
          >
            {pills.map((p) => {
              const rank = order.findIndex((o) => o.index === p.index); // the place in the order of play of this round
              return (
                <li key={p.index} className={view.to_act === p.index ? "active" : undefined}>
                  <span
                    className={rank === 0 ? "turnorder first" : "turnorder"}
                    title={rank === 0 ? "Plays first in this round" : `Plays ${ordinal(rank)} in this round`}
                  >
                    {ordinal(rank)}
                  </span>
                  <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} />
                  {s.rival && p.index === s.rival.index ? (
                    <span>Rival</span>
                  ) : (
                    // the name opens the board of the player (the computer and the techs)
                    <ChipName player={p.index} name={names[p.index] ?? `Player ${p.index + 1}`} />
                  )}
                  {p.organization ? <OrgName id={p.organization} className="orgname" /> : <span />}
                  <span
                    className="res"
                    title={finalTotal(p.index) === undefined ? "Victory points" : `Final score (the board scored ${p.score})`}
                  >
                    <ScoreIcon size={20} />
                    <b>{finalTotal(p.index) ?? p.score}</b>
                  </span>
                  {s.rival && p.index === s.rival.index ? (
                    <RivalCells view={view} />
                  ) : (
                    <>
                      <span className="res" title="Credits">
                        <CreditIcon size={18} />
                        <b>{p.credits}</b>
                      </span>
                      <span className="res" title="Energy">
                        <EnergyIcon size={18} />
                        <b>{p.energy}</b>
                      </span>
                      <span className="res" title="Publicity (the track ends at 10)">
                        <PublicityIcon size={18} />
                        <b>
                          {p.publicity}/{PUBLICITY_MAX}
                        </b>
                      </span>
                      <span className="res" title="Cards in the hand">
                        <DeckCardIcon size={18} />
                        <b>{view.counts.hands[p.index] ?? 0}</b>
                      </span>
                      <span className="res" title="Data in the pool (not the data in the computer)">
                        <DataIcon size={18} />
                        <b>{p.data_pool}</b>
                      </span>
                      {s.options.expansion ? (
                        <span className="res" title="Signal tokens">
                          <SignalTokenIcon size={18} />
                          <b>{p.signal_tokens}</b>
                        </span>
                      ) : null}
                      {oumuamua ? (
                        <span className="res" title="Exofossils">
                          <ExofossilIcon size={18} />
                          <b>{p.exofossils}</b>
                        </span>
                      ) : null}
                    </>
                  )}
                </li>
              );
            })}
          </ul>
          {topExtra ? <div className="extra">{topExtra}</div> : null}
        </div>
        {aboveMoves ? <div className="undobar">{aboveMoves}</div> : null}
        {moves ? <div className="movebar">{moves}</div> : null}
      </header>

      {results}

      <div className="gamegrid">
        <main className="col-center">
          <div className="boardwrap">
            <BoardView
              view={view}
              names={names}
              previous={previous}
              lastMove={lastMove}
              interaction={interaction}
              spots={spots && { ...spots, items: spots.items.filter((sp) => !sp.panel) }}
              goldChoice={goldChoice}
            />
            <RoundPiles view={view} />
          </div>
        </main>

        <aside className="col-aux" aria-label="Card row, tech stacks, organizations and publicity track">
          <RowDock view={view} row={row} inline flash={rowFlash} />
          <TechStacks view={view} pick={tech} />
          <OrgPanel view={view} names={names} spots={spots} />
          <MissionsPanel view={view} names={names} />
          <ArkhosPanel view={view} names={names} spots={spots} />
          <GlyphidsPanel view={view} names={names} spots={spots} />
          <PublicitySlot view={view} names={names} />
        </aside>
      </div>

      <SoloPanel view={view} spots={spots} />

      <BarHeight />
      <TrackerDock>
        <PlayerTracker view={view} names={names} previous={previous} />
      </TrackerDock>
      <RowDock view={view} row={row} flash={rowFlash} />
      <HandDock view={view} selection={hand} />
      <ExertianDock view={view} selection={hand} />
      {log}
      {chat}
      {overlay}
    </div>
  );
}
