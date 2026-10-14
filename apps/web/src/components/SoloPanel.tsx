// The solo game: the rival's board with its marker on the progress track, the data on its computer, its stored techs and action deck; and the
// player's objectives with the tasks that are marked. Everything comes from the engine's view; nothing is worked out here.
import { PLAYER_COLOR } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import { ScoreIcon } from "./Icons";
import { DataToken, Marker, PieceDefs, pieceColor } from "./Pieces";

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
                <img src={RIVAL_CARDS[id]} alt={`Rival action card ${id}`} width={330} height={367} loading="lazy" decoding="async" />
                <figcaption>{i + 1}</figcaption>
              </figure>
            ))}
          </div>
        </div>
        <div className="rcgroup">
          <h4>Action deck</h4>
          <figure className="rcard rcpile" title={`${view.counts.rival_deck} cards left in the rival's deck`}>
            <img src={RIVAL_CARDS.back} alt="The rival's action deck" width={330} height={367} loading="lazy" decoding="async" />
            <figcaption className="rccount">{view.counts.rival_deck}</figcaption>
          </figure>
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
        <li>Stored techs: {r.techs.length > 0 ? r.techs.join(", ") : <span className="muted">none</span>}</li>
      </ul>
    </section>
  );
}

function Objectives({ view }: { view: View }) {
  const ob = view.state.objectives;
  if (!ob) return null;
  return (
    <section className="objectives" aria-label="Objectives">
      <h3>
        Objectives{" "}
        <span className="muted small">
          {ob.pile.length} completed · {view.counts.objective_stack} in the stack
        </span>
      </h3>
      <div className="objrow">
        {ob.row.length === 0 ? <span className="muted">none</span> : null}
        {ob.row.map((id) => {
          const marks = ob.marks[id] ?? [];
          const done = marks.length > 0 && marks.every(Boolean);
          return (
            <figure key={id} className={done ? "objective done" : "objective"}>
              <img src={OBJECTIVES[id]} alt={`Objective ${id}`} width={240} height={239} loading="lazy" decoding="async" />
              <figcaption>
                {marks.map((m, i) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: a task of the tile
                  <span key={i} className={m ? "task on" : "task"} title={m ? `Task ${i + 1} marked` : `Task ${i + 1} not done`}>
                    {m ? "✓" : "○"}
                  </span>
                ))}
                {done ? <span className="muted small">complete</span> : null}
              </figcaption>
            </figure>
          );
        })}
      </div>
    </section>
  );
}

export function SoloPanel({ view }: { view: View }) {
  if (!view.state.rival) return null;
  return (
    <div className="solopanel">
      <Rival view={view} />
      <Objectives view={view} />
    </div>
  );
}
