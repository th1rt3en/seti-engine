"use client";
import { alienBack, cardImage } from "@/lib/cardImages";
// The base board with everything on it: the three discs turned to where the game has them, the four star boards in the order they were
// placed, the data and markers of every sector, the probes, orbiters and landers (each shown as its owner's figure), the markers on the
// species' discovery spaces, every player's score counter, the neutral markers still waiting at 20 and 30 points, and the moon token that
// marks the disc to rotate next. It draws what the game state says and works out no rule: the engine tells where each piece is,
// `lib/geometry.ts` tells where that is on the picture, and `Pieces.tsx` draws the pieces.
import {
  ALIEN,
  ALIEN_COLUMN,
  ALIEN_TOP,
  BOARD,
  CENTAURIAN_HEXES,
  CENTER,
  DIAL,
  DIAL_POCKET,
  DISC,
  DISCOVERY,
  GOLD,
  GOLD_EXTRA,
  GOLD_SLOTS,
  MOON,
  NEUTRAL_POCKETS,
  OUMUAMUA_TILE,
  PLANET,
  PLAYER_COLOR,
  RING_BOUNDS,
  RING_RADIUS,
  STAR,
  STAR_BOARD_HOME,
  alienColumn,
  goldPlace,
  polar,
  scoreDegrees,
  sectorDegrees,
} from "@/lib/geometry";
import { cardName } from "@/lib/moves";
import { SPECIES_SPACES } from "@/lib/speciesSpaces";
import { type Spot, onAlienBoard } from "@/lib/targets";
import { ZOOM_SECONDS, touchScreen } from "@/lib/touch";
import type { View } from "@seti/protocol";
import { type ReactNode, useRef, useState } from "react";
import { createPortal } from "react-dom";
import assets from "../generated/assets.json";
import expansionAssets from "../generated/expansion-assets.json";
import slotData from "../generated/slots.json";
import { type AnomalyToken, AnomalyTokenView } from "./Anomaly";
import { DataToken, Figure, Marker, type PieceColor, PieceDefs, ScorePawn, pieceColor } from "./Pieces";

const DISCS = assets.discs as Record<string, string>;
const TILES = assets.milestoneTiles as Record<string, string> & { white: string };
const SAMPLES = assets.samples as Record<string, string> & { back: string };
const GOLD_TILES = assets.gold as Record<string, { src: string; per: string; values: number[] }>;
const SLOTS = slotData as Record<string, { r: number; width: number; hi: number; lo: number }>;
/** The picture of a species board: the five of the base game and the three of the Space Agencies expansion. */
const EXPANSION_BOARDS = expansionAssets as Record<string, string>;
const alienFace = (species: string): string =>
  (assets.species as Record<string, string>)[species] ?? EXPANSION_BOARDS[`boards/${species}`] ?? assets.species.back;
const STAR_BOARDS = assets.starBoards as Record<string, string>;
/** How far (degrees) an Anomaly token lies from the middle of its sector: planets are about 20 degrees wide at the outermost ring. */
const ANOMALY_SIDE_DEGREES = 15;
const LANES = [1500, 1538, 1576, 1614];
const EXERTIAN_LANE = 1440; // the Exertian milestone tiles lie just inside the players' lanes // radius of each player's lane on the score track

/** Moving a probe: the probes that can be picked, the one that is, the spaces it can go to now (with what each takes and the way there). */
export interface BoardInteraction {
  probes: string[];
  selected: string | null;
  onSelectProbe: (id: string) => void;
  targets: { to: [number, number]; cost: number; path: [number, number][] }[];
  onTarget: (target: { to: [number, number]; cost: number; path: [number, number][] }) => void;
  /** The space picked, waiting to be confirmed ("ring-sector"): its route stays drawn. */
  chosen?: string | null;
}

/** Places that a move can be made at (landing, orbiting, a signal, a trace): highlighted on the board, and clicked to pick the move. */
/** Choosing a gold scoring tile to mark: the tiles that can be marked (by name), the one picked, and the click. The place taken is the leftmost free one of the tile. */
export interface GoldChoice {
  tiles: string[];
  selected: string | null;
  onPick: (tile: string) => void;
}

export interface BoardSpots {
  items: Spot[];
  selected: string | null;
  onSelect: (id: string) => void;
}

/** One space of the solar system as a wedge: its ring between two radii, its sector between two angles. */
function wedge(ring: number, sector: number): string {
  const [inner, outer] = [RING_BOUNDS[ring - 1] ?? 150, RING_BOUNDS[ring] ?? 372];
  const a0 = 45 * sector;
  const a1 = a0 + 45;
  const p = (r: number, a: number): string => {
    const at = polar(r, a);
    return `${at.x.toFixed(1)} ${at.y.toFixed(1)}`;
  };
  return `M ${p(outer, a0)} A ${outer} ${outer} 0 0 0 ${p(outer, a1)} L ${p(inner, a1)} A ${inner} ${inner} 0 0 1 ${p(inner, a0)} Z`;
}

/** `previous` is the view before this one: what changed since then is shown moving (a marker taking the place of a data token). */
export function BoardView({
  view,
  names,
  previous,
  interaction,
  spots,
  goldChoice,
}: {
  view: View;
  names: string[];
  previous?: View | null;
  interaction?: BoardInteraction;
  spots?: BoardSpots;
  goldChoice?: GoldChoice;
}) {
  const s = view.state;
  const [hover, setHover] = useState<string | null>(null);
  // a gold scoring tile is shown larger, upright and with its markers when the pointer rests on it for a second (or when it is tapped)
  const [goldZoom, setGoldZoom] = useState<{ i: number; x: number; y: number } | null>(null);
  const goldTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const color = (i: number) => pieceColor(s.players[i]?.color);
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  const quarter = STAR.quarter * STAR.scale;
  const quarterOffset = [
    { x: 0, y: -quarter },
    { x: -quarter, y: -quarter },
    { x: -quarter, y: 0 },
    { x: 0, y: 0 },
  ];
  // the disc that turns next: the moon token lies in its big circle on the rotation dial
  const nextDisc = ((s.rotations % 3) + 1) as 1 | 2 | 3;

  // probes that share a space are drawn side by side
  const spaces = new Map<string, typeof s.probes>();
  for (const p of s.probes) {
    const key = `${p.ring}-${p.sector}`;
    spaces.set(key, [...(spaces.get(key) ?? []), p]);
  }

  return (
    <>
      <svg
        viewBox={`0 ${Math.floor(ALIEN_TOP)} ${BOARD.w + GOLD_EXTRA} ${BOARD.h - Math.floor(ALIEN_TOP)}`}
        className="board"
        role="img"
        aria-label="The game board"
      >
        <PieceDefs />
        <image href={assets.board} x={0} y={0} width={BOARD.w} height={BOARD.h} />
        {/* the species boards lie on the base board, over its edge at the top; their cut-outs show the discovery spaces */}
        {s.species.map((sp, i) => {
          const face = alienFace(sp.discovered ? sp.species : "back");
          return (
            <image
              // biome-ignore lint/suspicious/noArrayIndexKey: the two slots are fixed
              key={`alien-${i}`}
              href={face}
              x={(ALIEN.middleX[i] ?? 680) - ALIEN.centre * ALIEN.scale}
              y={ALIEN_TOP}
              width={ALIEN.w * ALIEN.scale}
              height={ALIEN.h * ALIEN.scale}
            >
              <title>{sp.discovered ? `Species ${i + 1}: ${sp.species}` : `Species ${i + 1}: not discovered yet`}</title>
            </image>
          );
        })}

        {s.species.map((sp, i) => {
          // the deck of a discovered species lies to the right of its board: its back with the cards left over it, and the card that lies face up
          if (!sp.discovered) return null;
          const back = alienBack(sp.species);
          const at = alienColumn(i);
          const faceUp = sp.face_up ? cardImage(sp.face_up) : undefined;
          return (
            <g key={`alien-deck-${sp.species}`}>
              {back ? (
                <g>
                  <image
                    href={back}
                    x={at.deck.x}
                    y={at.deck.y}
                    width={ALIEN_COLUMN.w}
                    height={ALIEN_COLUMN.h}
                    preserveAspectRatio="xMidYMid slice"
                  />
                  <circle cx={at.deck.x + ALIEN_COLUMN.w / 2} cy={at.deck.y + ALIEN_COLUMN.h / 2} r={92} className="deckcount" />
                  <text
                    x={at.deck.x + ALIEN_COLUMN.w / 2}
                    y={at.deck.y + ALIEN_COLUMN.h / 2 + 42}
                    textAnchor="middle"
                    className="deckcounttext"
                  >
                    {sp.deck.length}
                  </text>
                  <title>{`${sp.deck.length} cards left in the deck of ${sp.species}`}</title>
                </g>
              ) : null}
              {faceUp ? (
                <g>
                  <image href={faceUp} x={at.faceUp.x} y={at.faceUp.y} width={ALIEN_COLUMN.w} height={ALIEN_COLUMN.h} />
                  <title>{`The card that lies face up: ${cardName(sp.face_up)}`}</title>
                </g>
              ) : null}
            </g>
          );
        })}

        {s.gold_tiles.map((g, i) => {
          const info = GOLD_TILES[`${g.tile}-${g.side}`];
          if (!info) return null;
          const place = goldPlace(i);
          return (
            <g
              key={`gold-${g.tile}`}
              // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
              role="button"
              tabIndex={0}
              aria-label={`Gold scoring tile ${g.tile}, side ${g.side}: ${info.per}`}
              transform={`translate(${place.x} ${place.y}) rotate(${place.rotation}) scale(${GOLD.scale}) translate(${-GOLD.w / 2} ${-GOLD.h / 2})`}
              className="goldtile"
              onPointerEnter={(e) => {
                if (e.pointerType === "touch") return; // a tap shows it (onClick) and it goes away by itself
                const { clientX: x, clientY: y } = e;
                clearTimeout(goldTimer.current);
                goldTimer.current = setTimeout(() => setGoldZoom({ i, x, y }), 1000);
              }}
              onPointerLeave={() => {
                clearTimeout(goldTimer.current);
                setGoldZoom(null);
              }}
              onClick={(e) => {
                clearTimeout(goldTimer.current);
                if (goldZoom?.i === i) return setGoldZoom(null);
                setGoldZoom({ i, x: e.clientX, y: e.clientY });
                // on a touch screen the enlarged tile goes away after a few seconds, or when it is tapped
                if (touchScreen()) goldTimer.current = setTimeout(() => setGoldZoom(null), ZOOM_SECONDS * 1000);
              }}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setGoldZoom(goldZoom?.i === i ? null : { i, x: 400, y: 200 })}
            >
              <image href={info.src} x={0} y={0} width={GOLD.w} height={GOLD.h} />
              {g.markers.map((player, k) => {
                const at = GOLD_SLOTS[k] ?? GOLD_SLOTS[GOLD_SLOTS.length - 1] ?? { x: 0, y: 0 };
                return (
                  <Marker
                    key={`${player}-${at.x}`}
                    x={at.x}
                    y={at.y}
                    size={84}
                    color={color(player)}
                    title={`${who(player)}: marker on the ${g.tile} tile`}
                  />
                );
              })}
              {goldChoice?.tiles.includes(g.tile)
                ? (() => {
                    const at = GOLD_SLOTS[Math.min(g.markers.length, GOLD_SLOTS.length - 1)] ?? { x: 0, y: 0 };
                    return (
                      <g
                        // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
                        role="button"
                        tabIndex={0}
                        aria-label={`Mark the ${g.tile} gold scoring tile`}
                        className={goldChoice.selected === g.tile ? "spot chosen" : "spot"}
                        onClick={(e) => {
                          e.stopPropagation();
                          goldChoice.onPick(g.tile);
                        }}
                        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && goldChoice.onPick(g.tile)}
                      >
                        <circle cx={at.x} cy={at.y} r={70} className="spotshape goldspot" />
                      </g>
                    );
                  })()
                : null}
              <title>{`${g.tile} (side ${g.side}): ${info.per}`}</title>
            </g>
          );
        })}

        {([3, 2, 1] as const).map((n) => {
          const size = DISC[n].size * DISC[n].scale;
          const href = DISCS[n === 3 && s.oumuamua_placed ? "disc-3-oumuamua" : `disc-${n}`];
          return (
            <image
              key={n}
              href={href}
              x={CENTER.x - size / 2}
              y={CENTER.y - size / 2}
              width={size}
              height={size}
              transform={`rotate(${-45 * (s.disc_angles[n - 1] ?? 0)} ${CENTER.x} ${CENTER.y})`}
            />
          );
        })}

        {s.sector_order.map((boardId, position) => {
          const home = STAR_BOARD_HOME[boardId] ?? position;
          const at = quarterOffset[home] ?? { x: 0, y: 0 };
          return (
            <image
              key={boardId}
              href={STAR_BOARDS[String(boardId)]}
              x={CENTER.x + at.x}
              y={CENTER.y + at.y}
              width={quarter}
              height={quarter}
              transform={`rotate(${-(position - home) * 90} ${CENTER.x} ${CENTER.y})`}
            />
          );
        })}

        {(() => {
          // the data slot of the 'Oumuamua tile: markers take its places from the counter-clockwise end, the data tokens that are left lie after them
          const slot = s.species.find((sp) => sp.discovered && sp.species === "oumuamua");
          const tile = slot?.extra?.tile as { data: number; markers: number[] } | undefined;
          if (!s.oumuamua_placed || !tile) return null;
          const turn = 45 * (s.disc_angles[2] ?? 0);
          return OUMUAMUA_TILE.degrees.map((deg, k) => {
            const at = polar(OUMUAMUA_TILE.radius, deg + turn);
            const marker = tile.markers[k];
            if (marker !== undefined) {
              return (
                <Marker
                  key={`oum-${deg}`}
                  x={at.x}
                  y={at.y}
                  size={OUMUAMUA_TILE.size}
                  color={color(marker)}
                  title={`${who(marker)}: marker on the 'Oumuamua tile`}
                />
              );
            }
            return k < tile.markers.length + tile.data ? (
              <DataToken key={`oum-${deg}`} x={at.x} y={at.y} size={OUMUAMUA_TILE.size} title="Data on the 'Oumuamua tile" />
            ) : null;
          });
        })()}

        {s.sectors.map((sec, i) => {
          // The data of a star lies in its curved slot, first token at the counter-clockwise end. When a player marks a signal there, the leftmost
          // data token leaves the slot (for the player's data pile) and the player's marker takes its place.
          const slot = SLOTS[sec.star];
          if (!slot) return null;
          const centre = sectorDegrees(i);
          const pitch = (slot.hi - slot.lo) / sec.capacity;
          // the slots were measured on the picture of the ring, which is drawn at STAR.scale
          const radius = slot.r * STAR.scale;
          const size = slot.width * STAR.scale * 1.14;
          const before = previous?.state.sectors[i]?.markers.length ?? sec.markers.length;
          const extra = sec.markers.slice(sec.capacity);
          return (
            <g key={sec.star}>
              {Array.from({ length: sec.capacity }, (_, k) => {
                const at = polar(radius, centre + slot.hi - (k + 0.5) * pitch);
                const marker = sec.markers[k];
                // biome-ignore lint/suspicious/noArrayIndexKey: the places of a slot are fixed
                if (marker === undefined) return <DataToken key={`d${k}`} x={at.x} y={at.y} size={size} />;
                const fresh = k >= before;
                return (
                  // biome-ignore lint/suspicious/noArrayIndexKey: the places of a slot are fixed
                  <g key={`m${k}`}>
                    {fresh ? (
                      <g className="lift">
                        <DataToken x={at.x} y={at.y} size={size} />
                      </g>
                    ) : null}
                    <g className={fresh ? "pop" : undefined}>
                      <Marker x={at.x} y={at.y} size={size} color={color(marker)} title={`${who(marker)}: marker in ${sec.star}`} />
                    </g>
                  </g>
                );
              })}
              {extra.map((player, k) => {
                const at = polar(radius - 120, centre + slot.hi - 2 - k * 3.2);
                return (
                  // biome-ignore lint/suspicious/noArrayIndexKey: markers are placed in order and never reorder
                  <Marker key={`x${k}`} x={at.x} y={at.y} size={64} color={color(player)} />
                );
              })}
              <title>{`${sec.star}: ${sec.data_remaining} of ${sec.capacity} data left; markers: ${sec.markers.map(who).join(", ") || "none"}; won by ${sec.winners.map(who).join(", ") || "nobody"}`}</title>
            </g>
          );
        })}

        {/* the Anomaly tokens (ALIEN-ANO-01): on the outermost ring, a little to the side of the middle of their sector so that they never cover Uranus
            or Neptune; they stay where they are while the discs turn, Earth moves to them */}
        {s.species.flatMap((sp) =>
          sp.discovered && sp.species === "anomalies"
            ? ((sp.extra?.tokens ?? []) as AnomalyToken[]).map((tok) => (
                <AnomalyTokenView
                  key={`anomaly-${tok.sector}`}
                  token={tok}
                  at={polar(RING_RADIUS[4] ?? 870, sectorDegrees(tok.sector) - ANOMALY_SIDE_DEGREES)}
                />
              ))
            : [],
        )}

        {Array.from(spaces.entries()).flatMap(([key, group]) => {
          const [ring, sector] = key.split("-").map(Number) as [number, number];
          const at = polar(RING_RADIUS[ring] ?? 270, sectorDegrees(sector));
          return group.map((p, k) => {
            const a = (2 * Math.PI * k) / group.length;
            const dx = group.length > 1 ? 46 * Math.cos(a) : 0;
            const dy = group.length > 1 ? 46 * Math.sin(a) : 0;
            const title = `${who(p.player)}: ${p.capsule ? "sample capsule" : "probe"} (ring ${p.ring}, sector ${p.sector})`;
            const pick = interaction?.probes.includes(p.id) ?? false;
            const chosen = interaction?.selected === p.id;
            const piece = p.capsule ? (
              <g key={p.id}>
                <Marker x={at.x + dx} y={at.y + dy} size={78} color={color(p.player)} title={title} />
                {/* the sample token that the capsule carries: its face for its owner (who may look), its back for the others (ALIEN-MASC-04) */}
                <image
                  href={SAMPLES[p.sample !== null && p.sample !== undefined && p.sample >= 0 ? String(p.sample) : "back"] ?? SAMPLES.back}
                  x={at.x + dx + 6}
                  y={at.y + dy - 66}
                  width={60}
                  height={60}
                >
                  <title>{p.player === view.viewer ? "The sample that this capsule carries" : "A sample, face down"}</title>
                </image>
              </g>
            ) : (
              <Figure key={p.id} x={at.x + dx} y={at.y + dy} color={color(p.player)} title={title} />
            );
            return pick ? (
              <g
                key={p.id}
                className={chosen ? "probe pickable chosen" : "probe pickable"}
                // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
                role="button"
                tabIndex={0}
                aria-pressed={chosen}
                aria-label={`Select probe ${p.id}`}
                onClick={() => interaction?.onSelectProbe(p.id)}
                onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && interaction?.onSelectProbe(p.id)}
              >
                <circle cx={at.x + dx} cy={at.y + dy + 6} r={chosen ? 84 : 70} className="pickring" />
                {piece}
              </g>
            ) : (
              <g key={p.id}>{piece}</g>
            );
          });
        })}

        {interaction?.targets.map((t) => {
          const key = `${t.to[0]}-${t.to[1]}`;
          const centre = polar(RING_RADIUS[t.to[0]] ?? 270, sectorDegrees(t.to[1]));
          const route = hover === key || interaction.chosen === key ? t.path : [];
          return (
            <g
              key={key}
              className="target"
              // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
              role="button"
              tabIndex={0}
              aria-label={`Move there for ${t.cost} movement`}
              onClick={() => interaction.onTarget(t)}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && interaction.onTarget(t)}
              onMouseEnter={() => setHover(key)}
              onMouseLeave={() => setHover(null)}
            >
              <path d={wedge(t.to[0], t.to[1])} className="targetcell" />
              {route.length > 0 ? (
                <polyline
                  points={route
                    .map(([r, c]) => {
                      const at = polar(RING_RADIUS[r] ?? 270, sectorDegrees(c));
                      return `${at.x},${at.y}`;
                    })
                    .join(" ")}
                  className="route"
                />
              ) : null}
              <circle cx={centre.x} cy={centre.y} r={38} className="targetcost" />
              <text x={centre.x} y={centre.y + 17} className="targettext" textAnchor="middle">
                {t.cost}
              </text>
            </g>
          );
        })}

        {Object.entries(PLANET).map(([name, pos]) => {
          const st = s.planets[name];
          if (!st) return null;
          const mascamites = s.species.find((sp) => sp.discovered && sp.species === "mascamites");
          const samples = ((mascamites?.extra.samples ?? {}) as Record<string, number[]>)[name]?.length ?? 0;
          return (
            <g key={name}>
              {/* the sample tokens lying face down on Jupiter and Saturn */}
              {Array.from({ length: samples }, (_, k) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: identical face-down tokens, only their count matters
                <g key={`sample-${name}-${k}`} transform={`translate(${pos.x + pos.r * 0.45 + k * 30} ${pos.y - pos.r * 0.75 - k * 14})`}>
                  <title>{`${samples} sample${samples === 1 ? "" : "s"} face down on ${name}`}</title>
                  <image href={SAMPLES.back} x={-38} y={-38} width={76} height={76} />
                </g>
              ))}
              {st.orbiters.map((player, k) => (
                <g
                  // biome-ignore lint/suspicious/noArrayIndexKey: arrival order
                  key={`o${k}`}
                  transform={`translate(${pos.x - pos.r * 0.55 + k * 84} ${pos.y - pos.r * 0.32})`}
                >
                  <ellipse cy={10} rx={74} ry={26} fill="none" stroke="#fff" strokeWidth={7} opacity={0.95} />
                  <Figure x={0} y={0} color={color(player)} title={`${who(player)}: orbiter at ${name}`} />
                </g>
              ))}
              {st.landers.map((player, k) => (
                <g
                  // biome-ignore lint/suspicious/noArrayIndexKey: arrival order
                  key={`l${k}`}
                  transform={`translate(${pos.x - pos.r * 0.55 + k * 84} ${pos.y + pos.r * 0.22})`}
                >
                  <rect x={-44} y={46} width={88} height={12} rx={5} fill="#fff" stroke="#000" strokeWidth={3} />
                  <Figure x={0} y={0} color={color(player)} title={`${who(player)}: lander at ${name}`} />
                </g>
              ))}
              {Object.entries(st.moon_landers ?? {}).map(([moon, player]) => {
                const at = MOON[moon.toLowerCase().split(/[ _]/)[0] ?? ""];
                return at ? (
                  <g key={moon} transform={`translate(${at.x} ${at.y})`}>
                    <rect x={-44} y={46} width={88} height={12} rx={5} fill="#fff" stroke="#000" strokeWidth={3} />
                    <Figure x={0} y={0} color={color(player)} title={`${who(player)}: lander on ${moon}`} />
                  </g>
                ) : null;
              })}
            </g>
          );
        })}

        {/* the message tiles that cover the reward hexes of the Centaurian board (ALIEN-CEN-04): the tile of the player who took the reward */}
        {s.species.flatMap((sp, i) => {
          if (!sp.discovered || sp.species !== "centaurians") return [];
          const covered = (sp.extra?.covered ?? []) as (number | null)[];
          return covered.map((player, k) => {
            const x = CENTAURIAN_HEXES.xs[k];
            if (player === null || player === undefined || x === undefined) return null;
            const at = onAlienBoard(i, x, CENTAURIAN_HEXES.y);
            const h = CENTAURIAN_HEXES.tileHeight * ALIEN.scale;
            const colour = s.players[player]?.color === "red" ? "orange" : (s.players[player]?.color ?? "white");
            return (
              <image
                // biome-ignore lint/suspicious/noArrayIndexKey: the four hexes are fixed
                key={`cen-hex-${i}-${k}`}
                href={TILES[colour] ?? TILES.white}
                x={at.x - (h * 72) / 128 / 2}
                y={at.y - h / 2}
                width={(h * 72) / 128}
                height={h}
              >
                <title>{`${who(player)}: message tile covers this reward`}</title>
              </image>
            );
          });
        })}

        {/* the markers on the spaces of a species board that have been taken, and on its overflow spaces (under the discovery spaces) */}
        {s.species.map((sp, i) => {
          const marks: ReactNode[] = [];
          if (sp.discovered) {
            for (const [colour, spaces] of Object.entries(sp.board)) {
              spaces.forEach((players, k) => {
                const at = SPECIES_SPACES[sp.species]?.[colour]?.[k];
                if (!at) return;
                const base = onAlienBoard(i, at[0], at[1]);
                players.forEach((player, n) => {
                  // a top capsule takes any number of markers: each later one lies a little higher
                  marks.push(
                    <Marker
                      // biome-ignore lint/suspicious/noArrayIndexKey: markers are placed in order and never reorder
                      key={`sb-${i}-${colour}-${k}-${n}`}
                      x={base.x}
                      y={base.y - n * 22}
                      size={86}
                      color={color(player)}
                      title={`${who(player)}: marker on the ${colour} space of ${sp.species}`}
                    />,
                  );
                });
              });
            }
          }
          sp.overflow.forEach((player, n) => {
            const colour = sp.overflow_kinds[n] ?? "pink";
            const at = DISCOVERY[i]?.[["pink", "yellow", "blue"].indexOf(colour)];
            if (!at) return;
            marks.push(
              <Marker
                // biome-ignore lint/suspicious/noArrayIndexKey: markers are placed in order and never reorder
                key={`of-${i}-${n}`}
                x={at.x}
                y={at.y + 190 - sp.overflow_kinds.slice(0, n).filter((c) => c === colour).length * 20}
                size={80}
                color={color(player)}
                title={`${who(player)}: marker on the ${colour} overflow space`}
              />,
            );
          });
          return marks;
        })}

        {s.species.slice(0, 2).map((sp, i) =>
          sp.discovery_spaces.map((mark, k) => {
            const at = DISCOVERY[i]?.[k];
            if (!at || mark === null) return null;
            const neutral = mark === "n";
            const player = neutral ? -1 : Number(mark.slice(1));
            return (
              <Marker
                key={`${sp.discovery_spaces.join("")}-${i}-${k}`}
                x={at.x}
                y={at.y}
                size={92}
                color={neutral ? "neutral" : color(player)}
                title={neutral ? "Neutral marker" : `${who(player)}: marker on a discovery space`}
              />
            );
          }),
        )}

        {/* the neutral markers still waiting in their pockets next to 20 and 30 points: the first player to pass the line makes one of them block the leftmost discovery space */}
        {(["20", "30"] as const).flatMap((at) =>
          NEUTRAL_POCKETS[at].slice(0, s.neutral_markers[at] ?? 0).map((pocket, k) => (
            <Marker
              // biome-ignore lint/suspicious/noArrayIndexKey: the pockets are fixed
              key={`n${at}-${k}`}
              x={pocket.x}
              y={pocket.y}
              size={76}
              color="neutral"
              title={`Neutral marker waiting at ${at} points: the first player to pass ${at} makes it block the leftmost discovery space`}
            />
          )),
        )}

        {/* the Exertian milestone tiles: shared, 20 and 40 points ahead of the leader at discovery; the second costs 1 credit to play a card */}
        {(
          (s.species.find((sp) => sp.discovered && sp.species === "exertians")?.extra.milestones ?? []) as {
            at: number;
            cost: number;
            done: number[];
          }[]
        ).map((m, k) => {
          const at = polar(EXERTIAN_LANE, scoreDegrees(m.at));
          return (
            <g key={`exm-${m.at}`} opacity={m.done.length >= s.players.length ? 0.4 : 1}>
              <title>{`Exertian milestone ${k + 1} at ${m.at} points: play an Exertian card face down${m.cost > 0 ? ` (costs ${m.cost} credit)` : ""}`}</title>
              {/* the tile lies along the track, its arrow pointing the way the markers go (clockwise) */}
              <image
                href={TILES[m.cost > 0 ? "exertian-credit" : "exertian"]}
                x={-70}
                y={-44}
                width={140}
                height={88}
                transform={`translate(${at.x} ${at.y}) rotate(${-scoreDegrees(m.at)})`}
              />
            </g>
          );
        })}

        {/* the Centaurian message tiles (one per player, 15 points ahead at discovery) and the message markers of the cards in front of the players */}
        {s.players.flatMap((p) => [
          ...p.messages.map((target) => {
            const at = polar(LANES[p.index] ?? 1500, scoreDegrees(target));
            return (
              <g key={`msg-${p.index}-${target}`}>
                <title>{`${who(p.index)}: Centaurian message milestone at ${target} points`}</title>
                {/* the +15 tile of the player's colour (the supply has white, green, purple and orange: the red player has the orange one) */}
                <image
                  href={TILES[p.color === "red" ? "orange" : p.color] ?? TILES.white}
                  x={-36}
                  y={-64}
                  width={72}
                  height={128}
                  transform={`translate(${at.x} ${at.y}) rotate(${-scoreDegrees(target)})`}
                />
              </g>
            );
          }),
          ...p.message_cards.map((m, n) => {
            const at = polar(LANES[p.index] ?? 1500, scoreDegrees(m.target));
            return (
              <Marker
                key={`mc-${p.index}-${m.card}-${n}`}
                x={at.x}
                y={at.y}
                size={68}
                color={color(p.index)}
                title={`${who(p.index)}: message marker of ${m.card} at ${m.target} points (resolved in the order sent)`}
              />
            );
          }),
        ])}

        {s.players.map((p) => {
          const at = polar(LANES[p.index] ?? 1500, scoreDegrees(p.score));
          return (
            <ScorePawn key={p.index} x={at.x} y={at.y - 6} size={84} color={color(p.index)} title={`${who(p.index)}: ${p.score} points`} />
          );
        })}

        <g transform={`translate(${DIAL[nextDisc].x} ${DIAL[nextDisc].y})`}>
          <image href={assets.moon} x={-DIAL_POCKET / 2} y={-DIAL_POCKET / 2} width={DIAL_POCKET} height={DIAL_POCKET} />
          <title>{`Next rotation: ${nextDisc === 1 ? "ring 1" : nextDisc === 2 ? "rings 1 and 2" : "rings 1, 2 and 3"}`}</title>
        </g>
        {spots?.items.map((sp) => (
          <g
            key={sp.id}
            // biome-ignore lint/a11y/useSemanticElements: an SVG group cannot be a button element
            role="button"
            tabIndex={0}
            aria-label={sp.label}
            className={spots.selected === sp.id ? "spot chosen" : "spot"}
            onClick={() => spots.onSelect(sp.id)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && spots.onSelect(sp.id)}
          >
            {sp.shape.kind === "circle" ? (
              <circle cx={sp.shape.x} cy={sp.shape.y} r={sp.shape.r} className="spotshape" />
            ) : sp.shape.kind === "rect" ? (
              <rect x={sp.shape.x} y={sp.shape.y} width={sp.shape.w} height={sp.shape.h} rx={26} className="spotshape" />
            ) : (
              <path d={sp.shape.d} className="spotshape" />
            )}
          </g>
        ))}
      </svg>
      {goldZoom && s.gold_tiles[goldZoom.i] ? (
        <GoldZoom
          tile={s.gold_tiles[goldZoom.i] as { tile: string; side: string }}
          markers={s.gold_tiles[goldZoom.i]?.markers ?? []}
          at={goldZoom}
          onClose={() => setGoldZoom(null)}
          colorOf={color}
          whoOf={who}
        />
      ) : null}
    </>
  );
}

/** A gold scoring tile enlarged and upright, with the markers on it (what the pointer rests on). */
function GoldZoom({
  tile,
  markers,
  at,
  onClose,
  colorOf,
  whoOf,
}: {
  tile: { tile: string; side: string };
  markers: number[];
  at: { x: number; y: number };
  onClose: () => void;
  colorOf: (i: number) => PieceColor;
  whoOf: (i: number) => string;
}) {
  const info = GOLD_TILES[`${tile.tile}-${tile.side}`];
  if (!info || typeof document === "undefined") return null;
  const width = Math.min(480, window.innerWidth - 16);
  const left = Math.max(8, Math.min(at.x + 18, window.innerWidth - width - 8));
  const top = Math.max(8, Math.min(at.y - 120, window.innerHeight - 440));
  return createPortal(
    // biome-ignore lint/a11y/useKeyWithClickEvents: it goes away by itself, and when the pointer leaves the tile
    <div
      className="goldzoom"
      style={{ left, top, width, pointerEvents: touchScreen() ? "auto" : undefined }}
      role="tooltip"
      onClick={onClose}
    >
      <svg viewBox={`0 0 ${GOLD.w} ${GOLD.h}`} role="img" aria-label={`Gold scoring tile ${tile.tile}`}>
        <PieceDefs />
        <image href={info.src} x={0} y={0} width={GOLD.w} height={GOLD.h} />
        {markers.map((player, k) => {
          const slot = GOLD_SLOTS[k] ?? GOLD_SLOTS[GOLD_SLOTS.length - 1] ?? { x: 0, y: 0 };
          return <Marker key={`${player}-${slot.x}`} x={slot.x} y={slot.y} size={84} color={colorOf(player)} title={whoOf(player)} />;
        })}
      </svg>
      <p>
        <b>{tile.tile}</b> (side {tile.side}): {info.per}. Points for the first, second and later choosers: {info.values.join(", ")}.
        {markers.length > 0 ? ` Chosen by ${markers.map(whoOf).join(", ")}.` : " Nobody has chosen it yet."}
      </p>
    </div>,
    document.body,
  );
}
