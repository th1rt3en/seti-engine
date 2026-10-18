// A game as one viewer sees it: a bar on top with the round, the turn, what the game is waiting for and the moves to choose from; the card row
// and the alien species on the left; the board in the middle; the publicity track and the tech stacks to its right; the tracker of all players
// floating at the right edge; the hand floating in the bottom left corner. The live game and the replay both use it. It works out no rule:
// everything comes from the engine's view.
import { PLAYER_COLOR } from "@/lib/geometry";
import { type DecisionSource, sourceLabel } from "@/lib/sources";
import type { View } from "@seti/protocol";
import type { ReactNode } from "react";
import { AmoebaPanel } from "./AmoebaPanel";
import { ArkhosPanel } from "./ArkhosPanel";
import { BarFold } from "./BarFold";
import { BarHeight } from "./BarHeight";
import { type BoardInteraction, type BoardSpots, BoardView, type GoldChoice } from "./BoardView";
import { ChipName } from "./ChipName";
import { GlyphidsPanel } from "./GlyphidsPanel";
import { ExertianDock, HandDock, type HandSelection } from "./HandDock";
import { Hint } from "./Hint";
import { CreditIcon, EnergyIcon, ExofossilIcon, PublicityIcon, ScoreIcon, SignalTokenIcon } from "./Icons";
import { MissionsPanel } from "./MissionsPanel";
import { OrgName } from "./OrgName";
import { OrgPanel } from "./OrgPanel";
import { PlayerTracker } from "./PlayerTracker";
import { PublicityTrack } from "./PublicityTrack";
import { RoundPiles } from "./RoundPiles";
import { RowDock, type RowSelection } from "./RowDock";
import { SoloPanel } from "./SoloPanel";
import { type TechPick, TechStacks } from "./TechStacks";
import { TrackerDock } from "./TrackerDock";

const ROUNDS = 5;

/** What the engine waits for, in words. */
const DECISION: Record<string, string> = {
  setup_tuck: "tuck a card for income",
  helion_tuck: "tuck a card for income",
  breach: "breach a security card, or not",
  income_tuck: "tuck a card for income, or skip",
  discard_to_four: "discard down to four cards",
  take_round_card: "take an end-of-round card",
  data_overflow: "place data first, or take the data",
  sector_order: "choose which completed sector to resolve next",
  gold_choice: "mark a gold scoring tile",
  signal: "mark a signal",
  trace: "mark a trace",
  scan_step: "scan",
  take_card: "take a card",
  land_free: "land for free",
  orbit_land_free: "orbit or land for free",
  land_data_slot: "cover a first-lander space: the one with 2 data or the one with 1 data",
  message_reward: "cover a message reward",
  exertian_play: "play an Exertian card, or not",
  research_tech: "take a tech",
  computer_slot: "choose a computer slot",
};

const humanize = (kind: string): string => DECISION[kind] ?? kind.replace(/_/g, " ");

/** Which step of the scan the player is at, from the moves the engine offers (the steps come from left to right, as on the player board). */
function scanStepText(types: Set<string>): string {
  if (types.has("scan_earth")) return "Scan, step 1: mark a signal in Earth's sector (or next to it, with the telescope tech)";
  if (types.has("scan_discard")) return "Scan, step 2: discard a card of the card row to mark a signal in a sector of its color";
  if (types.has("scan_token")) return "Scan, signal tokens: discard a token and another card of the card row for a signal, or skip";
  if (types.has("scan_mercury")) return "Scan, step 3: spend 1 publicity to mark a signal in Mercury's sector, or skip";
  if (types.has("scan_hand_discard"))
    return "Scan, step 4: discard a card from your hand to mark a signal in a sector of its color, or skip";
  if (types.has("scan_probe")) return "Scan, step 5: spend 1 energy to launch a probe, or gain 1 free movement, or skip";
  return "Scan: no step is left, finish the scan";
}

export function promptOf(view: View, names: string[]): { who: string; mine: boolean; text: string } {
  const s = view.state;
  const actor = view.to_act;
  if (s.phase === "finished") return { who: "", mine: false, text: "Game over" };
  if (actor === null) return { who: "", mine: false, text: "Starting..." };
  const mine = view.viewer !== null && actor === view.viewer;
  const who = s.rival && actor === s.rival.index ? "Rival" : (names[actor] ?? `Player ${actor + 1}`);
  const decision = s.pending[0];
  if (mine) {
    if (decision?.kind === "scan_step") return { who, mine, text: scanStepText(new Set(view.legal.map((m) => String(m.type)))) };
    if (decision) return { who, mine, text: humanize(decision.kind) };
    return { who, mine, text: s.main_done ? "take free actions, or end the turn" : "choose a main action" };
  }
  return { who, mine, text: decision ? `must ${humanize(decision.kind)}` : "is taking a turn" };
}

export function GameView({
  view,
  names,
  moves,
  topExtra,
  previous,
  hand,
  row,
  tech,
  log,
  overlay,
  context,
  rowFlash,
  contextActions,
  hint,
  interaction,
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
  /** Places on the board that a move can be made at (landing, orbiting, signals, traces). */
  spots?: BoardSpots;
  /** Marking a gold scoring tile. */
  goldChoice?: GoldChoice;
  /** The moves of the player to act (and the buttons that go with them): shown in the bar on top. */
  moves?: ReactNode;
  /** Connection and clock information for the bar. */
  topExtra?: ReactNode;
}) {
  const s = view.state;
  // exofossils exist once 'Oumuamua is face up: they show with the other resources (ALIEN-OUM-02)
  const oumuamua = s.species.some((sp) => sp.discovered && sp.species === "oumuamua");
  const prompt = promptOf(view, names);
  // what caused the decision that is asked now, at the end of the bar: "(Helion Assembly)"
  const cause = sourceLabel(
    s.pending[0]?.source as DecisionSource | null | undefined,
    s.sectors.map((sec) => sec.star),
    s.species.map((sp, i) => (sp.discovered ? sp.species.charAt(0).toUpperCase() + sp.species.slice(1) : `Species ${i + 1}`)),
  );
  const actor = view.to_act === null ? undefined : s.players[view.to_act];
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
                <b className="who">
                  {prompt.who ? `${prompt.who}${prompt.mine ? " (you)" : ""}${prompt.mine || context ? ":" : ""}` : " "}
                </b>
                <span className={context ? "prompt asking" : "prompt"}>
                  {context ?? prompt.text}
                  {cause && view.state.pending.length > 0 ? ` (${cause})` : ""}
                </span>
              </div>
              {contextActions ? <div className="contextactions">{contextActions}</div> : null}
            </div>
            {hint ? <Hint>{hint}</Hint> : null}
          </div>
          <ul className="scorechips" aria-label="Scores">
            {s.players.map((p) => (
              <li key={p.index} className={view.to_act === p.index ? "active" : undefined}>
                <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} />
                {s.rival && p.index === s.rival.index ? (
                  "Rival"
                ) : (
                  // the name opens the board of the player (the computer and the techs)
                  <ChipName player={p.index} name={names[p.index] ?? `Player ${p.index + 1}`} />
                )}
                {p.organization ? <OrgName id={p.organization} className="orgname" /> : null}
                <span className="res" title="Victory points">
                  <ScoreIcon size={20} />
                  <b>{p.score}</b>
                </span>
                {s.rival && p.index === s.rival.index ? null : (
                  <>
                    <span className="res" title="Credits">
                      <CreditIcon size={18} />
                      <b>{p.credits}</b>
                    </span>
                    <span className="res" title="Energy">
                      <EnergyIcon size={18} />
                      <b>{p.energy}</b>
                    </span>
                    <span className="res" title="Publicity">
                      <PublicityIcon size={18} />
                      <b>{p.publicity}</b>
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
            ))}
          </ul>
          {topExtra ? <div className="extra">{topExtra}</div> : null}
        </div>
        {moves ? <div className="movebar">{moves}</div> : null}
      </header>

      <div className="gamegrid">
        <main className="col-center">
          <div className="boardwrap">
            <BoardView
              view={view}
              names={names}
              previous={previous}
              interaction={interaction}
              spots={spots && { ...spots, items: spots.items.filter((sp) => !sp.panel) }}
              goldChoice={goldChoice}
            />
            <RoundPiles view={view} />
          </div>
        </main>

        <aside className="col-aux" aria-label="Publicity track and tech stacks">
          <PublicityTrack view={view} names={names} />
          <TechStacks view={view} pick={tech} />
          <RowDock view={view} row={row} inline flash={rowFlash} />
          <MissionsPanel view={view} names={names} />
          <OrgPanel view={view} names={names} spots={spots} />
          <ArkhosPanel view={view} names={names} spots={spots} />
          <GlyphidsPanel view={view} names={names} spots={spots} />
          <AmoebaPanel view={view} names={names} spots={spots} />
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
      {overlay}
    </div>
  );
}
