"use client";
// The base board with everything on it: the three discs turned to where the game has them, the four star boards in the order they were
// placed, the data and markers of every sector, the probes, orbiters and landers (each shown as its owner's figure), the markers on the
// species' discovery spaces, every player's score counter, the neutral markers still waiting at 20 and 30 points, and the moon token that
// marks the disc to rotate next. It draws what the game state says and works out no rule: the engine tells where each piece is,
// `lib/geometry.ts` tells where that is on the picture, and `Pieces.tsx` draws the pieces.
import {
  BOARD,
  CENTER,
  DIAL,
  DIAL_POCKET,
  DISC,
  DISCOVERY,
  MOON,
  NEUTRAL_POCKETS,
  PLANET,
  RING_BOUNDS,
  RING_RADIUS,
  STAR,
  STAR_BOARD_HOME,
  polar,
  scoreDegrees,
  sectorDegrees,
} from "@/lib/geometry";
import type { View } from "@seti/protocol";
import { useState } from "react";
import assets from "../generated/assets.json";
import slotData from "../generated/slots.json";
import { DataToken, Figure, Marker, PieceDefs, ScorePawn, pieceColor } from "./Pieces";

const DISCS = assets.discs as Record<string, string>;
const SLOTS = slotData as Record<string, { r: number; width: number; hi: number; lo: number }>;
const STAR_BOARDS = assets.starBoards as Record<string, string>;
const LANES = [1500, 1538, 1576, 1614]; // radius of each player's lane on the score track

/** Moving a probe: the probes that can be picked, the one that is, the spaces it can go to now (with what each takes and the way there). */
export interface BoardInteraction {
  probes: string[];
  selected: string | null;
  onSelectProbe: (id: string) => void;
  targets: { to: [number, number]; cost: number; path: [number, number][] }[];
  onTarget: (target: { to: [number, number]; cost: number; path: [number, number][] }) => void;
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
}: { view: View; names: string[]; previous?: View | null; interaction?: BoardInteraction }) {
  const s = view.state;
  const [hover, setHover] = useState<string | null>(null);
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
    <svg viewBox={`0 0 ${BOARD.w} ${BOARD.h}`} className="board" role="img" aria-label="The game board">
      <PieceDefs />
      <image href={assets.board} x={0} y={0} width={BOARD.w} height={BOARD.h} />

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
            <Marker key={p.id} x={at.x + dx} y={at.y + dy} size={78} color={color(p.player)} title={title} />
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
        const route = hover === key ? t.path : [];
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
        return (
          <g key={name}>
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
    </svg>
  );
}
