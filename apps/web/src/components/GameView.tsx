// A game as one viewer sees it: a bar on top with the round, the turn, what the game is waiting for and the moves to choose from; the card row
// and the alien species on the left; the board in the middle; the publicity track and the tech stacks to its right; the tracker of all players
// floating at the right edge; the hand floating in the bottom left corner. The live game and the replay both use it. It works out no rule:
// everything comes from the engine's view.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import type { ReactNode } from "react";
import assets from "../generated/assets.json";
import { AlienBoards } from "./AlienBoards";
import { BarHeight } from "./BarHeight";
import { type BoardInteraction, BoardView } from "./BoardView";
import { CardImage } from "./CardImage";
import { HandDock, type HandSelection } from "./HandDock";
import { CreditIcon, EnergyIcon } from "./Icons";
import { PlayerTracker } from "./PlayerTracker";
import { PublicityTrack } from "./PublicityTrack";
import { RoundPiles } from "./RoundPiles";
import { SoloPanel } from "./SoloPanel";
import { StateView } from "./StateView";
import { type TechPick, TechStacks } from "./TechStacks";
import { TrackerDock } from "./TrackerDock";

const ROUNDS = 5;

/** Picking a card of the card row (or the deck): which can be picked, which is, and what happens on a click. The sources are the engine's: "deck" and "row:<place>". */
export interface RowSelection {
  selectable: string[];
  selected: string | null;
  onSelect: (source: string) => void;
}

/** What the engine waits for, in words. */
const DECISION: Record<string, string> = {
  setup_tuck: "tuck a card for income",
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
  land_data_slot: "take a first-lander space",
  message_reward: "cover a message reward",
  exertian_play: "play an Exertian card, or not",
  research_tech: "take a tech",
  computer_slot: "choose a computer slot",
};

const humanize = (kind: string): string => DECISION[kind] ?? kind.replace(/_/g, " ");

export function promptOf(view: View, names: string[]): { who: string; mine: boolean; text: string } {
  const s = view.state;
  const actor = view.to_act;
  if (s.phase === "finished") return { who: "", mine: false, text: "Game over" };
  if (actor === null) return { who: "", mine: false, text: "Starting..." };
  const mine = view.viewer !== null && actor === view.viewer;
  const who = s.rival && actor === s.rival.index ? "Rival" : (names[actor] ?? `Player ${actor + 1}`);
  const decision = s.pending[0];
  if (mine) {
    if (decision) return { who, mine, text: `Your decision: ${humanize(decision.kind)}` };
    return { who, mine, text: s.main_done ? "Your turn: take free actions, or end the turn" : "Your turn: choose a main action" };
  }
  return { who, mine, text: decision ? `${who} must ${humanize(decision.kind)}` : `Waiting for ${who}` };
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
  interaction,
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
  /** Picking a probe and a space to move it to. */
  interaction?: BoardInteraction;
  /** The moves of the player to act (and the buttons that go with them): shown in the bar on top. */
  moves?: ReactNode;
  /** Connection and clock information for the bar. */
  topExtra?: ReactNode;
}) {
  const s = view.state;
  const prompt = promptOf(view, names);
  const actor = view.to_act === null ? undefined : s.players[view.to_act];
  return (
    <div className="game">
      <header className="topbar" aria-label="Round, turn, current player and moves">
        <div className="toprow">
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
            <div>
              <b className="who">{prompt.who ? `${prompt.who}${prompt.mine ? " (you)" : ""}` : " "}</b>
              <div className="prompt">{prompt.text}</div>
            </div>
          </div>
          <ul className="scorechips" aria-label="Scores">
            {s.players.map((p) => (
              <li key={p.index} className={view.to_act === p.index ? "active" : undefined}>
                <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} />
                {s.rival && p.index === s.rival.index ? "Rival" : (names[p.index] ?? `Player ${p.index + 1}`)} <b>{p.score}</b>
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
        <aside className="col-left">
          <section className="cardrow" aria-label="Card row">
            <h3>
              Card row{" "}
              <span className="muted small">
                deck {view.counts.deck} · discard {s.discard.length}
              </span>
            </h3>
            <div className="cards">
              {s.card_row.length === 0 ? <span className="muted">empty</span> : null}
              {s.card_row.map((c, i) => {
                const source = `row:${i}`;
                if (!row?.selectable.includes(source)) {
                  // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                  return <CardImage key={`${c}-${i}`} id={c} size="row" />;
                }
                return (
                  <button
                    // biome-ignore lint/suspicious/noArrayIndexKey: the slot is the identity of a card of the row
                    key={`${c}-${i}`}
                    type="button"
                    className={row.selected === source ? "cardbtn selectable selected" : "cardbtn selectable"}
                    aria-pressed={row.selected === source}
                    onClick={() => row.onSelect(source)}
                  >
                    <CardImage id={c} size="row" />
                  </button>
                );
              })}
              {row?.selectable.includes("deck") ? (
                <button
                  type="button"
                  className={row.selected === "deck" ? "cardbtn selectable selected deckbtn" : "cardbtn selectable deckbtn"}
                  aria-pressed={row.selected === "deck"}
                  onClick={() => row.onSelect("deck")}
                  title="The top card of the deck"
                >
                  <img src={assets.cardBack} alt="Top of the deck" width={300} height={418} className="cardimg decktile" />
                  <span className="decklabel">Deck {view.counts.deck}</span>
                </button>
              ) : null}
            </div>
          </section>
          <AlienBoards view={view} names={names} />
        </aside>

        <main className="col-center">
          <div className="boardwrap">
            <BoardView view={view} names={names} previous={previous} interaction={interaction} />
            <RoundPiles view={view} />
          </div>
        </main>

        <aside className="col-aux" aria-label="Publicity track and tech stacks">
          <PublicityTrack view={view} names={names} />
          <TechStacks view={view} pick={tech} />
        </aside>
      </div>

      <SoloPanel view={view} />

      <details className="more">
        <summary>All details (techs, planets, gold tiles, sectors)</summary>
        <StateView view={view} names={names} />
      </details>

      <BarHeight />
      <TrackerDock>
        <PlayerTracker view={view} names={names} previous={previous} />
      </TrackerDock>
      <HandDock view={view} selection={hand} />
      {log}
    </div>
  );
}
