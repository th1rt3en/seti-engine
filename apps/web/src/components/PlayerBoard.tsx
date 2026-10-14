"use client";
// A player's board: the computer with its six spaces (the data placed in it) and the four tech slots behind spaces 1, 3, 5 and 6 (the computer techs
// placed there, with the data on their lower space), the probe and telescope techs, and the data pool. What a player has in the computer is public,
// so everybody can look at every board at any time. There is no picture of the board among the assets (docs/asset-gaps.md): it is drawn here, with the
// tech tiles as they are printed. When a player has researched a computer tech and must choose its slot, the free slots are highlighted and clicked.
import { PLAYER_COLOR } from "@/lib/geometry";
import { TECH_INFO } from "@/lib/techs";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import { DeckCardIcon, PublicityIcon } from "./Icons";
import { DataToken, PieceDefs } from "./Pieces";

const FRONTS = assets.techFronts as Record<string, string>;
const GLYPHS = ["dot", "link", "branch", "cross"] as const;
/** The places of the computer techs: behind the 1st, 3rd, 5th and 6th space of the top row (the engine's numbers 0, 2, 4, 5). */
const SLOT_POSITIONS = [0, 2, 4, 5];
const SPACE_X = (i: number): number => 110 + i * 156;
const TILE = { w: 112, h: 157 };

/** Picking the slot of a computer tech that was just taken: the free slots (the engine's numbers), the one that is picked, and the click. */
export interface SlotChoice {
  slots: number[];
  selected: number | null;
  onPick: (slot: number) => void;
}

/** Asks the panel to show the board of a player (the tracker has a button for each player). */
export const OPEN_BOARD_EVENT = "seti-open-board";

function Icon({ x, y, size, children }: { x: number; y: number; size: number; children: React.ReactNode }) {
  return (
    <svg x={x} y={y} width={size} height={size} overflow="visible" aria-hidden="true">
      {children}
    </svg>
  );
}

/** One slot of the computer for a tech: the tech that lies there with the data on its lower space, or an empty slot (that can be picked). */
function Slot({ p, pos, choice }: { p: View["state"]["players"][number]; pos: number; choice?: SlotChoice }) {
  const x = SPACE_X(pos) - TILE.w / 2;
  const y = 215;
  const placed = p.computer_techs[String(pos)];
  const choosable = choice?.slots.includes(pos) ?? false;
  const front = placed ? FRONTS[placed.tech] : undefined;
  const body = (
    <>
      <line x1={x + TILE.w / 2} y1={194} x2={x + TILE.w / 2} y2={y} stroke="#6aa6ff" strokeWidth="4" />
      {front ? (
        <>
          <image href={front} x={x} y={y} width={TILE.w} height={TILE.h} />
          {placed?.lower_filled ? <DataToken x={x + TILE.w / 2} y={y + TILE.h * 0.82} size={46} title="Data on the lower space" /> : null}
          <title>{`${TECH_INFO[placed?.tech ?? ""]?.name ?? placed?.tech}: ${TECH_INFO[placed?.tech ?? ""]?.effect ?? ""}`}</title>
        </>
      ) : (
        <>
          <rect
            x={x}
            y={y}
            width={TILE.w}
            height={TILE.h}
            rx="12"
            fill="#0a1226"
            stroke="#6aa6ff"
            strokeWidth="3"
            strokeDasharray="10 8"
            opacity="0.7"
          />
          <text x={x + TILE.w / 2} y={y + TILE.h / 2} textAnchor="middle" className="pbhint">
            tech slot
          </text>
        </>
      )}
      {choosable ? (
        <rect
          x={x - 6}
          y={y - 6}
          width={TILE.w + 12}
          height={TILE.h + 12}
          rx="16"
          className={choice?.selected === pos ? "spotshape slotchosen" : "spotshape"}
          style={{ strokeWidth: 6 }}
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

function Board({ view, player, choice }: { view: View; player: number; choice?: SlotChoice }) {
  const p = view.state.players[player];
  if (!p) return null;
  const techs = new Set(p.techs);
  return (
    <svg viewBox="0 0 1000 650" className="playerboard" role="img" aria-label={`The board of player ${player + 1}`}>
      <PieceDefs />
      <defs>
        <linearGradient id="pb-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#1b2a4a" />
          <stop offset="1" stopColor="#0f1830" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="992" height="642" rx="26" fill="url(#pb-bg)" stroke={PLAYER_COLOR[p.color] ?? "#fff"} strokeWidth="6" />

      <text x="30" y="52" className="pbtitle">
        Computer
      </text>
      {Array.from({ length: 6 }, (_, i) => {
        const x = SPACE_X(i);
        return (
          <g key={`space-${x}`}>
            <circle cx={x} cy={140} r={54} fill="#0a1226" stroke="#6aa6ff" strokeWidth="5" />
            <text x={x} y={86} textAnchor="middle" className="pbnum">
              {i + 1}
            </text>
            {p.computer[i] ? <DataToken x={x} y={140} size={88} title={`Data on space ${i + 1}`} /> : null}
            {i === 1 ? (
              <Icon x={x + 28} y={160} size={34}>
                <PublicityIcon size={34} />
              </Icon>
            ) : null}
            {i === 3 ? (
              <Icon x={x + 28} y={160} size={34}>
                <DeckCardIcon size={34} />
              </Icon>
            ) : null}
          </g>
        );
      })}

      {SLOT_POSITIONS.map((pos) => (
        <Slot key={`slot-${pos}`} p={p} pos={pos} choice={choice} />
      ))}

      {(["probe", "telescope"] as const).map((category, c) => (
        <g key={category}>
          <text x={40 + c * 480} y="436" className="pbtitle">
            {category === "probe" ? "Probe techs" : "Telescope techs"}
          </text>
          {GLYPHS.map((glyph, j) => {
            const name = `${category}-${glyph}`;
            const x = 40 + c * 480 + j * 112;
            const owned = techs.has(name);
            return (
              <g key={name}>
                {owned ? (
                  <>
                    <image href={FRONTS[name]} x={x} y={452} width={96} height={135} />
                    <title>{`${TECH_INFO[name]?.name ?? name}: ${TECH_INFO[name]?.effect ?? ""}`}</title>
                  </>
                ) : (
                  <>
                    <rect
                      x={x}
                      y={452}
                      width={96}
                      height={135}
                      rx="10"
                      fill="#0a1226"
                      stroke="#6aa6ff"
                      strokeWidth="2"
                      strokeDasharray="8 7"
                      opacity="0.5"
                    />
                    <title>{`${TECH_INFO[name]?.name ?? name}: not researched`}</title>
                  </>
                )}
              </g>
            );
          })}
        </g>
      ))}

      <text x="40" y="623" className="pbtitle">
        Data pool
      </text>
      {Array.from({ length: 6 }, (_, i) => (
        <g key={`pool-${SPACE_X(i)}`}>
          <circle cx={230 + i * 70} cy={615} r={26} fill="#0a1226" stroke="#6aa6ff" strokeWidth="3" opacity="0.8" />
          {i < p.data_pool ? <DataToken x={230 + i * 70} y={615} size={44} title="Data in the pool" /> : null}
        </g>
      ))}
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
}: { view: View; names: string[]; shown: number; onShow: (player: number) => void; onClose: () => void; choice?: SlotChoice }) {
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
      <Board view={view} player={shown} choice={shown === view.viewer ? choice : undefined} />
    </section>
  );
}
