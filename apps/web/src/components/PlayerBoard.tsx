"use client";
import { cardImage } from "@/lib/cardImages";
// A player's board: the computer with its six spaces (the data placed in it) and the four tech slots behind spaces 1, 3, 5 and 6 (the computer techs
// placed there, with the data on their lower space), the probe and telescope techs, and the data pool. What a player has in the computer is public,
// so everybody can look at every board at any time. The picture is the printed board (supplied by the owner); the data, the techs, the income and the
// missions are drawn over it at the places measured on the picture. When a player has researched a computer tech and must choose its slot, the free
// slots are highlighted and clicked.
import { PLAYER_COLOR } from "@/lib/geometry";
import { glyphToken } from "@/lib/glyphids";
import { cardName } from "@/lib/moves";
import { TECH_INFO } from "@/lib/techs";
import type { View } from "@seti/protocol";
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";
import { DataToken, PieceDefs } from "./Pieces";

const FRONTS = assets.techFronts as Record<string, string>;
const BOARD = assets.playerBoard as { src: string; w: number; h: number };
const GLYPHS = ["dot", "link", "branch", "cross"] as const;
/** The places of the computer techs: behind the 1st, 3rd, 5th and 6th space of the computer (the engine's numbers 0, 2, 4, 5). */
const SLOT_POSITIONS = [0, 2, 4, 5];
/** The picture is the colorful panel of the printed board; the page adds a header with the income above it and the missions below it. */
const HEAD = 96;
/** The six computer spaces on the picture of the board (the centre of each, all in one row). */
const SPACE = { x: [346, 420, 502, 572, 660, 747], y: HEAD + 227 };
/** The diameter of the data token and of the highlight of the free action "place data", centred on each computer space. The 2nd and 4th spaces (the
 * publicity and the income icons) are printed smaller, but their data token is drawn as large as the others. */
const SPACE_DIAMETER = [40, 40, 40, 40, 40, 40];
const TILE = { w: 84, h: 118 };
/** On the picture of a computer tech (175 x 246) its upper circle, which lies over the printed space, is centred 30.5% down; the dashed circle for the
 * data of its lower space is centred 70% down and is as wide as the upper one. */
const TILE_UPPER = 0.305;
const TILE_LOWER = 0.7;
/** The columns of the probe and telescope techs on the picture, by glyph (dot, link, branch, cross). */
const TECH_X: Record<"probe" | "telescope", number[]> = { probe: [108, 192, 343, 432], telescope: [628, 782, 866, 955] };
const TECH_Y = HEAD + 32;
/** The blue base where the data pool lies (the data not yet in the computer). */
const POOL = { x: [175, 210, 245], y: [HEAD + 225, HEAD + 265] };
/** The strip under the board with the glyph tokens a player owns (Glyphids, EXP-GLY-04). */
const GLYPH_STRIP = 84;
const GLYPH_KINDS = ["black", "blue", "cyan", "orange", "pink", "red", "yellow"];
const MISSIONS = { x: 20, w: 150, h: 208, gap: 14 };
const ICON = expansionAssets as Record<string, string>;
const PRINTED = assets.printedIcons as Record<string, string>;
/** The income of each kind in the header, with its printed icon. */
const INCOME_ICONS: [string, string | undefined][] = [
  ["card", PRINTED["card-random"]],
  ["energy", ICON["tokens/icon-energy"]],
  ["credit", ICON["tokens/icon-credit"]],
  ["publicity", ICON["tokens/icon-publicity"]], // shown only when the player has that income (an organization)
  ["data", ICON["tokens/icon-data"]],
];

/** Picking the slot of a computer tech that was just taken: the free slots (the engine's numbers), the one that is picked, and the click. */
export interface SlotChoice {
  slots: number[];
  selected: number | null;
  onPick: (slot: number) => void;
}

/** Placing data on the lower space of a computer tech (a free action, TECH-21): the slots (the engine's numbers) that can take it, and the click. */
export interface LowerChoice {
  slots: number[];
  onPlace: (slot: number) => void;
}

/** One slot of the computer for a tech: the tech that lies there with the data on its lower space, or nothing (when it can be picked it is highlighted). */
function Slot({ p, pos, choice, lower }: { p: View["state"]["players"][number]; pos: number; choice?: SlotChoice; lower?: LowerChoice }) {
  const x = (SPACE.x[pos] ?? 0) - TILE.w / 2;
  const y = SPACE.y - TILE.h * TILE_UPPER;
  const placed = p.computer_techs[String(pos)];
  const choosable = choice?.slots.includes(pos) ?? false;
  const front = placed ? FRONTS[placed.tech] : undefined;
  const body = (
    <>
      {front ? (
        <>
          <image href={front} x={x} y={y} width={TILE.w} height={TILE.h} />
          {placed?.lower_filled ? (
            <DataToken
              x={x + TILE.w / 2}
              y={y + TILE.h * TILE_LOWER}
              size={(SPACE_DIAMETER[0] ?? 40) / 0.88}
              title="Data on the lower space"
            />
          ) : null}
          <title>{`${TECH_INFO[placed?.tech ?? ""]?.name ?? placed?.tech}: ${TECH_INFO[placed?.tech ?? ""]?.effect ?? ""}`}</title>
        </>
      ) : null}
      {placed && lower?.slots.includes(pos) && !placed.lower_filled ? (
        <g
          // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
          role="button"
          tabIndex={0}
          aria-label="Place 1 data on the lower space of this computer tech (free action)"
          className="spot"
          onClick={() => lower.onPlace(pos)}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && lower.onPlace(pos)}
        >
          <circle
            cx={x + TILE.w / 2}
            cy={y + TILE.h * TILE_LOWER}
            r={(SPACE_DIAMETER[0] ?? 40) / 2 + 3}
            className="spotshape"
            style={{ strokeWidth: 5 }}
          />
          <title>Place 1 data here (free action)</title>
        </g>
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

function Board({
  view,
  player,
  choice,
  onPlaceData,
  lower,
}: { view: View; player: number; choice?: SlotChoice; onPlaceData?: () => void; lower?: LowerChoice }) {
  const p = view.state.players[player];
  if (!p) return null;
  const techs = new Set(p.techs);
  const income = view.trackers?.[player]?.income ?? {};
  // the free action "place data" (FREE-03) puts one data of the pool in the leftmost empty space: that space is the one to click
  const next = onPlaceData ? p.computer.indexOf(false) : -1;
  const rows = Math.max(1, Math.ceil(p.missions.length / 6));
  // the glyph tokens the player owns, when the Glyphids are on the board: one token per kind with how many, under the picture
  const glyphids = view.state.species.some((sp) => sp.discovered && sp.species === "glyphids");
  const strip = glyphids ? GLYPH_STRIP : 0;
  const owned = GLYPH_KINDS.map((kind) => ({ kind, n: (p.glyphs ?? []).filter((g) => g === kind).length })).filter((o) => o.n > 0);
  // the cards in front of the player, in the order they were played (public): Centaurian message cards, then the Exertian cards played face down
  const messages = p.message_cards ?? [];
  const played = p.exertian_played ?? [];
  const front = [
    ...messages.map((m) => ({
      key: `msg-${m.card}`,
      kind: "message",
      card: m.card as string | null,
      label: `Message card ${cardName(m.card)}: marker at ${m.target} points`,
    })),
    // the Exertian cards played face down show their back until the game is over; then the engine sends the cards to everybody
    ...played.map((c, i) => ({
      key: `exo-${i}`,
      kind: "exertian",
      card: cardImage(c) ? (c as string | null) : null,
      label: cardImage(c)
        ? `Exertian card ${cardName(c)} (${i + 1}), turned over at the end of the game`
        : `Exertian card played face down (${i + 1})`,
    })),
  ];
  const frontRows = Math.ceil(front.length / 6);
  const frontY = HEAD + BOARD.h + strip + 26 + rows * (MISSIONS.h + 50);
  const height = frontY + (frontRows > 0 ? 40 + frontRows * (MISSIONS.h + 30) : 0) + 6;
  return (
    <svg viewBox={`0 0 ${BOARD.w} ${height}`} className="playerboard" role="img" aria-label={`The board of player ${player + 1}`}>
      <PieceDefs />
      <rect
        x={2}
        y={2}
        width={BOARD.w - 4}
        height={height - 4}
        rx={26}
        fill="#0f1830"
        stroke={PLAYER_COLOR[p.color] ?? "#fff"}
        strokeWidth={5}
      />
      {/* the header: the income of each kind (the income card plus the tucked cards) */}
      <image href={PRINTED.income} x={24} y={22} width={52} height={52}>
        <title>Income each round</title>
      </image>
      <text x={90} y={60} className="pbtitle">
        Income each round
      </text>
      {INCOME_ICONS.filter(([kind]) => ["card", "energy", "credit"].includes(kind) || (income[kind] ?? 0) > 0).map(([kind, src], i) => (
        <g key={kind}>
          {src ? <image href={src} x={380 + i * 130} y={24} width={kind === "card" ? 40 : 52} height={52} /> : null}
          <text x={380 + i * 130 + 58} y={62} className="pbincome light">
            {income[kind] ?? 0}
          </text>
        </g>
      ))}
      <image href={BOARD.src} x={0} y={HEAD} width={BOARD.w} height={BOARD.h} />

      {SLOT_POSITIONS.map((pos) => (
        <Slot key={`slot-${pos}`} p={p} pos={pos} choice={choice} lower={lower} />
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
              <circle
                cx={x}
                cy={SPACE.y}
                r={(SPACE_DIAMETER[i] ?? 40) / 2 + 3}
                fill="rgba(255,209,102,0.2)"
                stroke="#ffd166"
                strokeWidth={4}
                strokeDasharray="8 5"
              />
            ) : null}
            {p.computer[i] ? (
              <DataToken x={x} y={SPACE.y} size={(SPACE_DIAMETER[i] ?? 40) / 0.88} title={`Data on space ${i + 1}`} />
            ) : null}
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
        <text x={210} y={HEAD + 295} textAnchor="middle" className="pbincome light">
          +{p.data_pool - 6}
        </text>
      ) : null}

      {glyphids ? (
        <g>
          <title>{`Glyph tokens owned: ${(p.glyphs ?? []).length}`}</title>
          <text x={24} y={HEAD + BOARD.h + 52} className="pbtitle">
            Glyph tokens
          </text>
          <text x={250} y={HEAD + BOARD.h + 52} className="pbincome light">
            {(p.glyphs ?? []).length}
          </text>
          {owned.length === 0 ? (
            <text x={310} y={HEAD + BOARD.h + 52} className="pbhint">
              none yet
            </text>
          ) : null}
          {owned.map((o, i) => (
            <g key={o.kind} transform={`translate(${310 + i * 96} ${HEAD + BOARD.h + 12})`}>
              <image href={glyphToken(o.kind)} x={0} y={0} width={48} height={56}>
                <title>{`${o.n} ${o.kind} glyph token${o.n === 1 ? "" : "s"}`}</title>
              </image>
              <circle cx={58} cy={40} r={15} fill="rgba(8,12,26,0.92)" stroke="#fff" strokeWidth={2.5} />
              <text x={58} y={46} textAnchor="middle" fontSize={20} fontWeight={700} fill="#fff">
                {o.n}
              </text>
            </g>
          ))}
        </g>
      ) : null}

      {front.length > 0 ? (
        <g>
          <text x={MISSIONS.x} y={frontY + 22} className="pbcardtitle">
            In front of the player, in the order played
          </text>
          {front.map((f, i) => {
            const x = MISSIONS.x + (i % 6) * (MISSIONS.w + MISSIONS.gap);
            const y = frontY + 40 + Math.floor(i / 6) * (MISSIONS.h + 30);
            // a card played face down is an Exertian card: it shows the Exertian back, not the back of the main deck
            const src = f.card ? cardImage(f.card) : assets.alienBacks.exertians;
            return (
              <g key={f.key}>
                {src ? <image href={src} x={x} y={y} width={MISSIONS.w} height={MISSIONS.h} /> : null}
                {f.kind === "message" ? (
                  <text x={x + MISSIONS.w / 2} y={y + MISSIONS.h + 20} textAnchor="middle" className="pbhint">
                    message
                  </text>
                ) : null}
                <title>{f.label}</title>
              </g>
            );
          })}
        </g>
      ) : null}

      {/* the open missions lie on the board, with the circles that are covered */}
      {p.missions.map((m, i) => {
        const col = i % 6;
        const row = Math.floor(i / 6);
        const x = MISSIONS.x + col * (MISSIONS.w + MISSIONS.gap);
        const y = HEAD + BOARD.h + strip + 26 + row * (MISSIONS.h + 50);
        const src = cardImage(m.card);
        return (
          <g key={m.card}>
            {src ? <image href={src} x={x} y={y} width={MISSIONS.w} height={MISSIONS.h} /> : null}
            {m.kind === "trigger" ? (
              m.used.map((u, k) => (
                <circle
                  // biome-ignore lint/suspicious/noArrayIndexKey: the circles of a card are fixed
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
  lower,
}: {
  view: View;
  names: string[];
  shown: number;
  onShow: (player: number) => void;
  onClose: () => void;
  choice?: SlotChoice;
  /** The free action "place data": given when the viewer may do it; the first empty space of their computer is then clickable. */
  onPlaceData?: () => void;
  /** The free action "place data on a computer tech's lower space": the slots that can take it, highlighted on the board. */
  lower?: LowerChoice;
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
      {lower && lower.slots.length > 0 && shown === view.viewer ? (
        <p className="handhint">Click a highlighted data space under a computer tech to place a data from your pool there (free action).</p>
      ) : null}
      {onPlaceData && shown === view.viewer ? (
        <p className="handhint">Click the highlighted computer space to place a data from your pool (free action).</p>
      ) : null}
      <Board
        view={view}
        player={shown}
        choice={shown === view.viewer ? choice : undefined}
        onPlaceData={shown === view.viewer ? onPlaceData : undefined}
        lower={shown === view.viewer ? lower : undefined}
      />
    </section>
  );
}
