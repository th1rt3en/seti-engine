// The solo game: the rival's board with its marker on the progress track, the data on its computer, its stored techs and action deck; and the
// player's objectives with the tasks that are marked. Everything comes from the engine's view; nothing is worked out here.
import { PLAYER_COLOR } from "@/lib/geometry";
import { TECH_INFO } from "@/lib/techs";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";
import type { BoardSpots } from "./BoardView";
import { HelpTip } from "./HelpTip";
import { ScoreIcon } from "./Icons";
import { DataToken, Marker, PieceDefs, pieceColor } from "./Pieces";
import { openRivalDeck } from "./RivalDeckPanel";
import { TapZoomImage } from "./TapZoom";

const TECH_FRONTS = assets.techFronts as Record<string, string>;
const W = 1000;
const H = 325;
const TRACK = [
  "blue-dot",
  "blue-link",
  "blue-branch",
  "blue-cross",
  "pink-dot",
  "pink-link",
  "pink-branch",
  "pink-cross",
  "orange-dot",
  "orange-link",
  "orange-branch",
  "orange-cross",
];
const GLYPHS = ["dot", "link", "branch", "cross"];

// The 12 circles of the progress track are printed in the same places on every board, clockwise from the lower left, with the glyphs dot, link,
// branch, cross in each group of four. The colour of each group differs by board; the places were measured on the pictures (fractions of the picture).
const SLOTS: Record<string, [number, number][]> = {
  "1-2-star": [
    [0.68, 0.668],
    [0.669, 0.508],
    [0.681, 0.35],
    [0.713, 0.225],
    [0.861, 0.222],
    [0.895, 0.35],
    [0.905, 0.505],
    [0.895, 0.668],
    [0.863, 0.79],
    [0.815, 0.865],
    [0.759, 0.865],
    [0.713, 0.79],
  ],
  "3-star": [
    [0.679, 0.665],
    [0.668, 0.505],
    [0.68, 0.345],
    [0.712, 0.22],
    [0.861, 0.222],
    [0.894, 0.35],
    [0.904, 0.505],
    [0.894, 0.665],
    [0.861, 0.79],
    [0.813, 0.865],
    [0.758, 0.865],
    [0.711, 0.79],
  ],
  "4-star": [
    [0.683, 0.665],
    [0.672, 0.505],
    [0.684, 0.348],
    [0.716, 0.22],
    [0.864, 0.22],
    [0.898, 0.348],
    [0.908, 0.503],
    [0.898, 0.665],
    [0.866, 0.788],
    [0.817, 0.862],
    [0.762, 0.862],
    [0.716, 0.788],
  ],
  "5-star": [
    [0.684, 0.668],
    [0.672, 0.508],
    [0.685, 0.35],
    [0.717, 0.222],
    [0.866, 0.225],
    [0.898, 0.35],
    [0.909, 0.507],
    [0.898, 0.665],
    [0.866, 0.792],
    [0.818, 0.865],
    [0.763, 0.865],
    [0.715, 0.79],
  ],
};
const GROUP_COLORS: Record<string, string[]> = {
  "1-2-star": ["orange", "blue", "pink"],
  "3-star": ["blue", "pink", "orange"],
  "4-star": ["orange", "blue", "pink"],
  "5-star": ["pink", "orange", "blue"],
};
// the six circles of the rival's computer, left to right
const COMPUTER: [number, number][] = [0, 1, 2, 3, 4, 5].map((k) => [0.265 + 0.05 * k, 0.8]);

const boardOf = (difficulty: number): string => (difficulty <= 2 ? "1-2-star" : `${difficulty}-star`);
const BOARDS = assets.rivalBoards as Record<string, string>;
const OBJECTIVES = assets.objectives as Record<string, string>;
const RIVAL_CARDS = assets.rivalCards as Record<string, string>;
const EXPANSION = expansionAssets as Record<string, string>;
// the rival's cards of the expansion (EXP-SOLO-02, A-033): the extra starting card and the three species cards
const EXPANSION_RIVAL: Record<string, string> = { "SE.1": "rival-00", "SE.2": "rival-01", "SE.3": "rival-02", "SE.4": "rival-03" };
export const rivalCardImage = (id: string): string => RIVAL_CARDS[id] ?? EXPANSION[EXPANSION_RIVAL[id] ?? ""] ?? "";

/** The place of the rival's marker among the 12 circles of its progress track, as the board shows it (1 to 12, clockwise from the first circle after the growth icon at the top): the pill of the
 * rival says the same number. (The engine's own number is the place in its list of the spaces, which is not the order of the printed circles.) */
export function progressSpace(view: View): number | null {
  const r = view.state.rival;
  if (!r) return null;
  const board = boardOf(view.state.options.difficulty ?? 3);
  const [color = "blue", glyph = "dot"] = (TRACK[r.progress] ?? "blue-dot").split("-");
  const k = (GROUP_COLORS[board] ?? []).indexOf(color) * 4 + GLYPHS.indexOf(glyph);
  // the growth icon (the card at the top of the ring) lies between the circles 4 and 5 of the places above, on every board: the first circle after it is 1
  return k < 0 ? null : ((k + 8) % 12) + 1;
}

function Rival({ view }: { view: View }) {
  const s = view.state;
  const r = s.rival;
  if (!r) return null;
  const stars = s.options.difficulty ?? 3;
  const board = boardOf(stars);
  const [color = "blue", glyph = "dot"] = (TRACK[r.progress] ?? "blue-dot").split("-");
  const k = (GROUP_COLORS[board] ?? []).indexOf(color) * 4 + GLYPHS.indexOf(glyph);
  const at = SLOTS[board]?.[k];
  const me = s.players[r.index];
  return (
    <section className="rivalboard" aria-label="The rival's board">
      <h3>
        Rival{" "}
        <span className="muted small">
          {stars} star{stars === 1 ? "" : "s"}
        </span>
      </h3>
      <div className="rivalpic">
        <img src={BOARDS[board]} alt={`The rival's board, ${stars} stars`} width={1500} height={487} decoding="async" />
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="Rival progress and computer">
          <PieceDefs />
          {COMPUTER.slice(0, r.computer).map(([x, y], i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: a slot of the computer
            <DataToken key={i} x={x * W} y={y * H} size={34} title="Data on the rival's computer" />
          ))}
          {at ? (
            <Marker x={at[0] * W} y={at[1] * H} size={40} color={pieceColor(me?.color)} title={`Rival at ${TRACK[r.progress]}`} />
          ) : null}
        </svg>
      </div>
      <div className="rivalcards">
        <div className="rcgroup">
          <h4>
            Action cards played this round <span className="muted small">in the order played</span>
          </h4>
          <div className="rcrow">
            {r.used.length === 0 ? <span className="muted">none yet</span> : null}
            {r.used.map((id, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: the same card cannot be played twice in a round, but the order is the identity
              <figure key={`${id}-${i}`} className="rcard" title={`Card ${id}`}>
                <TapZoomImage src={rivalCardImage(id)} alt={`Rival action card ${id}`} width={330} height={367} />
                <figcaption>{i + 1}</figcaption>
              </figure>
            ))}
          </div>
        </div>
        <div className="rcgroup">
          <h4>Action deck</h4>
          <button
            type="button"
            className="rcard rcpile rcpeek"
            title={`${view.counts.rival_deck} cards left in the rival's deck: click to see which`}
            onClick={() => openRivalDeck()}
          >
            <img
              src={RIVAL_CARDS.back as string}
              alt="The rival's action deck: click to preview the unused cards"
              width={330}
              height={367}
            />
            <span className="rccount">{view.counts.rival_deck}</span>
          </button>
          <p className="muted small">Click the deck to see the cards that are left.</p>
        </div>
      </div>
      <ul className="rivalfacts">
        <li>
          <span className="dot" style={{ background: PLAYER_COLOR[me?.color ?? "white"] ?? "#fff" }} /> <ScoreIcon size={18} />{" "}
          <b>{me?.score ?? 0}</b> · Publicity <b>{me?.publicity ?? 0}</b>
        </li>
        <li>
          Advanced cards waiting <b>{r.advanced.length}</b> · Computer <b>{r.computer}</b>/6
        </li>
        <li className="rivaltechs">
          Techs researched (stored):{" "}
          {r.techs.length > 0 ? (
            r.techs.map((t) => (
              <span key={t} className="rivaltech" title={`${TECH_INFO[t]?.name ?? t}: ${TECH_INFO[t]?.effect ?? ""}`}>
                {TECH_FRONTS[t] ? (
                  <img src={TECH_FRONTS[t]} alt={TECH_INFO[t]?.name ?? t} width={30} height={42} className="mini-tech" />
                ) : (
                  t
                )}
              </span>
            ))
          ) : (
            <span className="muted">none</span>
          )}{" "}
          <span className="muted small">(a card that copies a tech of another player can take one of these)</span>
        </li>
      </ul>
    </section>
  );
}

/** What the objectives are worth to the rival: the numbers of the tiles, and the words of the tooltips that say how the rival gains from the open ones
 * (SOLO-OBJ-05 to SOLO-OBJ-07, EXP-SOLO-06). Everything counted is in the engine's view. */
export function objectiveFacts(view: View) {
  const s = view.state;
  const ob = s.objectives;
  if (!ob) return null;
  const done = (id: string): boolean => (ob.marks[id] ?? []).every(Boolean) && (ob.marks[id] ?? []).length > 0;
  const finishedOnTable = ob.row.filter(done).length; // done this turn: they join the pile at the end of the turn
  const unspent = ob.pile.length + finishedOnTable;
  const completed = (ob.spent ?? 0) + unspent;
  const openOnTable = ob.row.length - finishedOnTable;
  const inStack = view.counts.objective_stack;
  const left = openOnTable + inStack;
  const round = Math.min(s.round, 5);
  const longTerm = ob.long_term ?? [];
  const openLongTerm = longTerm.reduce((n, id) => n + (ob.marks[id] ?? []).filter((m) => !m).length, 0);
  const short = Math.max(0, round - unspent);
  return { completed, spent: ob.spent ?? 0, unspent, openOnTable, inStack, left, round, longTerm: longTerm.length, openLongTerm, short };
}

function Objectives({ view, spots }: { view: View; spots?: BoardSpots }) {
  const ob = view.state.objectives;
  const f = objectiveFacts(view);
  if (!ob || !f) return null;
  const spend =
    f.round <= 4 ? (
      <>
        At the end of round {f.round}, before income, you spend {f.round} completed objective{f.round === 1 ? "" : "s"} (1, 2, 3 and 4 after
        rounds 1 to 4). You have {f.unspent} to spend now:{" "}
        {f.short === 0 ? (
          "enough."
        ) : (
          <b>
            {f.short} short, so the rival would advance {3 * f.short} spaces on its progress track (3 for each one missing).
          </b>
        )}
      </>
    ) : (
      <>Nothing is spent after round 5: what counts now is every objective that is not completed.</>
    );
  return (
    <section className="objectives" aria-label="Objectives">
      <h3>
        Objectives{" "}
        <span className="muted small">
          <HelpTip
            tip={
              <>
                <b>Completed: {f.completed}</b> ({f.spent} spent in the earlier rounds, {f.unspent} waiting to be spent).
                <br />
                {spend}
              </>
            }
          >
            {f.completed} completed
          </HelpTip>{" "}
          ·{" "}
          <HelpTip
            tip={
              <>
                <b>Left: {f.left}</b> ({f.openOnTable} not completed on the table, {f.inStack} still in the stack).
                <br />
                At the end of round 5 the rival scores <b>5 points</b> for each objective that is not completed, those in the stack too:{" "}
                {f.left} × 5 = <b>{5 * f.left} points</b> if the game ended now.
              </>
            }
          >
            {f.left} left
          </HelpTip>
          {f.longTerm > 0 ? (
            <>
              {" "}
              ·{" "}
              <HelpTip
                tip={
                  <>
                    <b>Long-term tiles: {f.longTerm}</b> in play, {f.openLongTerm} open task{f.openLongTerm === 1 ? "" : "s"}. After each of
                    rounds 2, 3 and 4 the rival advances 1 space on its progress track for every open task of these tiles ({f.openLongTerm}{" "}
                    now). A finished long-term tile leaves the game; it is never spent and never scores for the rival.
                  </>
                }
              >
                {f.openLongTerm} long-term task{f.openLongTerm === 1 ? "" : "s"} open
              </HelpTip>
            </>
          ) : null}
        </span>
      </h3>
      <div className="objrow">
        {ob.row.length === 0 ? <span className="muted">none</span> : null}
        {[...ob.row, ...(ob.long_term ?? [])].map((id) => {
          const marks = ob.marks[id] ?? [];
          const done = marks.length > 0 && marks.every(Boolean);
          const longTerm = id.startsWith("LT-");
          const src = longTerm ? EXPANSION[`objectives/long-term-${id.slice(3)}`] : OBJECTIVES[id];
          return (
            <figure
              key={id}
              className={done ? "objective done" : "objective"}
              title={
                done
                  ? "Completed: it joins the pile at the end of the turn, and can be spent at the end of the round."
                  : longTerm
                    ? "Long-term: the rival advances 1 space for each open task after rounds 2 to 4."
                    : "Not completed: if it is still open at the end of round 5 the rival scores 5 points for it (and each missing completed objective at the end of rounds 1 to 4 gives it 3 spaces of progress)."
              }
            >
              <img
                src={src}
                alt={`${longTerm ? "Long-term objective" : "Objective"} ${id}`}
                width={240}
                height={239}
                loading="lazy"
                decoding="async"
              />
              <figcaption>
                {marks.map((m, i) => {
                  // a task that the player can mark now is a highlighted place on the tile (the player picks one when a trigger fits several)
                  const spot = spots?.items.find((sp) => sp.id === `task:${id}:${i}`);
                  const label = m ? `Task ${i + 1} marked` : `Task ${i + 1} not done`;
                  return spot && spots ? (
                    <button
                      // biome-ignore lint/suspicious/noArrayIndexKey: a task of the tile
                      key={i}
                      type="button"
                      className={spots.selected === spot.id ? "task pick chosen" : "task pick"}
                      aria-pressed={spots.selected === spot.id}
                      title={`Mark task ${i + 1}`}
                      onClick={() => spots.onSelect(spot.id)}
                    >
                      ○
                    </button>
                  ) : (
                    // biome-ignore lint/suspicious/noArrayIndexKey: a task of the tile
                    <span key={i} className={m ? "task on" : "task"} title={label}>
                      {m ? "✓" : "○"}
                    </span>
                  );
                })}
                {longTerm ? (
                  <span className="muted small">long-term: the rival advances for each open task after rounds 2 to 4</span>
                ) : null}
                {done ? <span className="muted small">complete</span> : null}
              </figcaption>
            </figure>
          );
        })}
      </div>
    </section>
  );
}

export function SoloPanel({ view, spots }: { view: View; spots?: BoardSpots }) {
  if (!view.state.rival) return null;
  return (
    <div className="solopanel">
      <Rival view={view} />
      <Objectives view={view} spots={spots} />
    </div>
  );
}
