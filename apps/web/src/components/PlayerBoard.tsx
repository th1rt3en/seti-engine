"use client";
import { cardImage } from "@/lib/cardImages";
// A player's board: the computer with its six spaces (the data placed in it) and the four tech slots behind spaces 1, 3, 5 and 6 (the computer techs
// placed there, with the data on their lower space), the probe and telescope techs, and the data pool. What a player has in the computer is public,
// so everybody can look at every board at any time. The picture is the printed board (supplied by the owner); the data, the techs, the income and the
// missions are drawn over it at the places measured on the picture. When a player has researched a computer tech and must choose its slot, the free
// slots are highlighted and clicked.
import { PLAYER_COLOR } from "@/lib/geometry";
import { TECH_INFO } from "@/lib/techs";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import { DataToken, PieceDefs } from "./Pieces";

const FRONTS = assets.techFronts as Record<string, string>;
const BOARD = assets.playerBoard as { src: string; w: number; h: number };
const GLYPHS = ["dot", "link", "branch", "cross"] as const;
/** The places of the computer techs: behind the 1st, 3rd, 5th and 6th space of the computer (the engine's numbers 0, 2, 4, 5). */
const SLOT_POSITIONS = [0, 2, 4, 5];
/** The six computer spaces on the picture of the board (the centre of each, all in one row). */
const SPACE = { x: [860, 939, 1015, 1088, 1169, 1255], y: 393 };
const TILE = { w: 84, h: 118 };
/** The columns of the probe and telescope techs on the picture, by glyph (dot, link, branch, cross). */
const TECH_X: Record<"probe" | "telescope", number[]> = { probe: [620, 704, 855, 944], telescope: [1140, 1294, 1378, 1467] };
const TECH_Y = 200;
/** The blue base where the data pool lies (the data not yet in the computer), and the five income squares at the top. */
const POOL = { x: [687, 722, 757], y: [393, 433] };
const INCOME_SQUARES: Record<string, number> = { card: 313, energy: 394, credit: 475 };
const MISSIONS = { x: 520, y: 540, w: 150, h: 208, gap: 14 };

/** Picking the slot of a computer tech that was just taken: the free slots (the engine's numbers), the one that is picked, and the click. */
export interface SlotChoice {
  slots: number[];
  selected: number | null;
  onPick: (slot: number) => void;
}

/** One slot of the computer for a tech: the tech that lies there with the data on its lower space, or nothing (when it can be picked it is highlighted). */
function Slot({ p, pos, choice }: { p: View["state"]["players"][number]; pos: number; choice?: SlotChoice }) {
  const x = (SPACE.x[pos] ?? 0) - TILE.w / 2;
  const y = SPACE.y - 46;
  const placed = p.computer_techs[String(pos)];
  const choosable = choice?.slots.includes(pos) ?? false;
  const front = placed ? FRONTS[placed.tech] : undefined;
  const body = (
    <>
      {front ? (
        <>
          <image href={front} x={x} y={y} width={TILE.w} height={TILE.h} />
          {placed?.lower_filled ? <DataToken x={x + TILE.w / 2} y={y + TILE.h * 0.82} size={34} title="Data on the lower space" /> : null}
          <title>{`${TECH_INFO[placed?.tech ?? ""]?.name ?? placed?.tech}: ${TECH_INFO[placed?.tech ?? ""]?.effect ?? ""}`}</title>
        </>
      ) : null}
      {choosable ? (
        <rect
          x={x - 4}
          y={y - 4}
          width={TILE.w + 8}
          height={TILE.h + 8}
          rx="12"
          className={choice?.selected === pos ? "spotshape slotchosen" : "spotshape"}
          style={{ strokeWidth: 5 }}
        />
      ) : null}
    </>
  );
  return choosable ? (
    <g
      // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
      role="button"
      tabIndex={0}
      aria-label={`Put the tech on computer space ${pos + 1}`}
      className="spot"
      onClick={() => choice?.onPick(pos)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && choice?.onPick(pos)}
    >
      {body}
    </g>
  ) : (
    <g>{body}</g>
  );
}

function Board({ view, player, choice, onPlaceData }: { view: View; player: number; choice?: SlotChoice; onPlaceData?: () => void }) {
  const p = view.state.players[player];
  if (!p) return null;
  const techs = new Set(p.techs);
  const income = view.trackers?.[player]?.income ?? {};
  // the free action "place data" (FREE-03) puts one data of the pool in the leftmost empty space: that space is the one to click
  const next = onPlaceData ? p.computer.indexOf(false) : -1;
  return (
    <svg viewBox={`0 0 ${BOARD.w} ${BOARD.h}`} className="playerboard" role="img" aria-label={`The board of player ${player + 1}`}>
      <PieceDefs />
      <image href={BOARD.src} x={0} y={0} width={BOARD.w} height={BOARD.h} />
      <rect
        x={4}
        y={4}
        width={BOARD.w - 8}
        height={BOARD.h - 8}
        rx={40}
        fill="none"
        stroke={PLAYER_COLOR[p.color] ?? "#fff"}
        strokeWidth={8}
      />

      {/* the income of each kind: the income card plus the tucked cards, in the squares above the icons */}
      {Object.entries(INCOME_SQUARES).map(([kind, x]) => (
        <text key={kind} x={x} y={101} textAnchor="middle" className="pbincome">
          {income[kind] ?? 0}
        </text>
      ))}

      {SLOT_POSITIONS.map((pos) => (
        <Slot key={`slot-${pos}`} p={p} pos={pos} choice={choice} />
      ))}

      {SPACE.x.map((x, i) => {
        const clickable = i === next;
        return (
          <g
            key={`space-${x}`}
            className={clickable ? "pbspace pickable" : undefined}
            {...(clickable
              ? {
                  role: "button",
                  tabIndex: 0,
                  "aria-label": `Place 1 data from your pool on computer space ${i + 1} (free action)`,
                  onClick: onPlaceData,
                  onKeyDown: (e: React.KeyboardEvent) => (e.key === "Enter" || e.key === " ") && onPlaceData?.(),
                }
              : {})}
          >
            {clickable ? <title>Place 1 data from your pool here (free action)</title> : null}
            {clickable ? (
              <circle cx={x} cy={SPACE.y} r={40} fill="rgba(255,209,102,0.2)" stroke="#ffd166" strokeWidth={6} strokeDasharray="10 6" />
            ) : null}
            {p.computer[i] ? <DataToken x={x} y={SPACE.y} size={56} title={`Data on space ${i + 1}`} /> : null}
          </g>
        );
      })}

      {(["probe", "telescope"] as const).map((category) =>
        GLYPHS.map((glyph, j) => {
          const name = `${category}-${glyph}`;
          const x = (TECH_X[category][j] ?? 0) - TILE.w / 2;
          return techs.has(name) ? (
            <g key={name}>
              <image href={FRONTS[name]} x={x} y={TECH_Y} width={TILE.w} height={TILE.h} />
              <title>{`${TECH_INFO[name]?.name ?? name}: ${TECH_INFO[name]?.effect ?? ""}`}</title>
            </g>
          ) : null;
        }),
      )}

      {/* the data pool lies on the blue base */}
      {Array.from({ length: Math.min(p.data_pool, 6) }, (_, i) => (
        <DataToken
          // biome-ignore lint/suspicious/noArrayIndexKey: identical tokens in a fixed grid
          key={`pool-${i}`}
          x={POOL.x[i % 3] ?? 0}
          y={POOL.y[Math.floor(i / 3)] ?? 0}
          size={38}
          title="Data in the pool"
        />
      ))}
      {p.data_pool > 6 ? (
        <text x={722} y={462} textAnchor="middle" className="pbincome">
          +{p.data_pool - 6}
        </text>
      ) : null}

      {/* the open missions lie on the board, with the circles that are covered */}
      {p.missions.map((m, i) => {
        const col = i % 6;
        const row = Math.floor(i / 6);
        const x = MISSIONS.x + col * (MISSIONS.w + MISSIONS.gap);
        const y = MISSIONS.y + row * (MISSIONS.h + 50);
        const src = cardImage(m.card);
        return (
          <g key={m.card}>
            {src ? <image href={src} x={x} y={y} width={MISSIONS.w} height={MISSIONS.h} /> : null}
            {m.kind === "trigger" ? (
              m.used.map((u, k) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: the circles of a card are fixed
                <circle
                  key={k}
                  cx={x + 20 + k * 30}
                  cy={y + MISSIONS.h + 20}
                  r={11}
                  fill={u ? "#6ef0a5" : "none"}
                  stroke="#fff"
                  strokeWidth={3}
                />
              ))
            ) : (
              <text x={x + MISSIONS.w / 2} y={y + MISSIONS.h + 26} textAnchor="middle" className="pbhint">
                quick mission
              </text>
            )}
            <title>{`Open mission ${m.card}`}</title>
          </g>
        );
      })}
    </svg>
  );
}

export function PlayerBoardPanel({
  view,
  names,
  shown,
  onShow,
  onClose,
  choice,
  onPlaceData,
}: {
  view: View;
  names: string[];
  shown: number;
  onShow: (player: number) => void;
  onClose: () => void;
  choice?: SlotChoice;
  /** The free action "place data": given when the viewer may do it; the first empty space of their computer is then clickable. */
  onPlaceData?: () => void;
}) {
  const s = view.state;
  const players = s.players.filter((p) => !(s.rival && p.index === s.rival.index));
  return (
    <section className="boardpanel" aria-label="Player boards">
      <header>
        <div className="boardtabs">
          {players.map((p) => (
            <button key={p.index} type="button" className={p.index === shown ? "chip on" : "chip"} onClick={() => onShow(p.index)}>
              <span className="dot" style={{ background: PLAYER_COLOR[p.color] ?? "#fff" }} /> {names[p.index] ?? `Player ${p.index + 1}`}
              {view.viewer === p.index ? " (you)" : ""}
            </button>
          ))}
        </div>
        <button type="button" className="secondary" onClick={onClose} aria-label="Close the player boards">
          ✕
        </button>
      </header>
      {choice ? <p className="handhint">Click the slot of the computer where the new tech goes.</p> : null}
      {onPlaceData && shown === view.viewer ? (
        <p className="handhint">Click the highlighted computer space to place a data from your pool (free action).</p>
      ) : null}
      <Board
        view={view}
        player={shown}
        choice={shown === view.viewer ? choice : undefined}
        onPlaceData={shown === view.viewer ? onPlaceData : undefined}
      />
    </section>
  );
}
