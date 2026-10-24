"use client";
// A preview of the solar system: the discs, the Sun, the sector boards and the probes, with two buttons: one turns the discs as the next rotation would
// (the engine worked out where everything is afterwards: View.rotation_previews, one for each of the next rotations), and one to the left of it puts them back where they are now.
// It only shows; nothing is played and nothing is sent to the game.
import { BOARD, CENTER, DISC, RING_RADIUS, STAR, STAR_BOARD_HOME, SUN_SIZE, TRACK, polar, sectorDegrees } from "@/lib/geometry";
import type { View } from "@seti/protocol";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import assets from "../generated/assets.json";
import { type PieceColor, pieceColor } from "./Pieces";
import { Marker, PieceDefs, ProbePiece } from "./Pieces";

const DISCS = assets.discs as Record<string, string>;
const STAR_BOARDS = assets.starBoards as Record<string, string>;
const QUARTER = STAR.quarter * STAR.scale;
const QUARTER_AT = [
  { x: 0, y: -QUARTER },
  { x: -QUARTER, y: -QUARTER },
  { x: -QUARTER, y: 0 },
  { x: 0, y: 0 },
];
// the part of the base board that is shown: a square around the solar system, as far as the score track (a crop of the board picture)
const VIEW = Math.round(TRACK.radius + 70);

export function SolarPreview({ view, names, onClose }: { view: View; names: string[]; onClose: () => void }) {
  // how many rotations are shown from now (0 is the solar system as it is)
  const [count, setCount] = useState(0);
  const s = view.state;
  const previews = view.rotation_previews ?? [];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (typeof document === "undefined") return null;
  const pv = count > 0 ? (previews[count - 1] ?? null) : null;
  const color = (i: number): PieceColor => pieceColor(s.players[i]?.color);
  const who = (i: number): string => (s.rival && i === s.rival.index ? "Rival" : (names[i] ?? `Player ${i + 1}`));
  const probes = pv ? pv.probes : s.probes;
  // the angle of a disc, counted without the wrap from 7 to 0 so that it always turns forward: its angle now plus a step for each rotation shown
  // that turned it (a rotation turns the disc it is its turn for, and every disc inside it)
  const angle = (n: number): number => (s.disc_angles[n - 1] ?? 0) + previews.slice(0, count).filter((q) => n <= q.disc).length;
  const turned = pv === null ? [] : [1, 2, 3].filter((n) => n <= pv.disc);
  const pushed = previews.slice(0, count).reduce((a, q) => a + q.pushed, 0);
  return createPortal(
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()} role="presentation">
      {/* biome-ignore lint/a11y/useSemanticElements: an overlay with its own backdrop, not a native <dialog> */}
      <div className="overlaybox solarpreview" role="dialog" aria-modal="true" aria-label="Solar system preview">
        <h2>Solar system preview</h2>
        <p className="muted small">
          {previews.length === 0
            ? "The preview is not available."
            : count === 0
              ? "The solar system as it is now."
              : `After ${count} rotation${count === 1 ? "" : "s"}. The last one turns ${turned.length > 1 ? `discs 1 to ${turned.length}` : "disc 1"}.${
                  pushed > 0 ? ` Probes are pushed ${pushed} time${pushed === 1 ? "" : "s"} on the way.` : ""
                }`}{" "}
          This is only a preview: nothing is played.
        </p>
        <svg
          viewBox={`${CENTER.x - VIEW} ${CENTER.y - VIEW} ${2 * VIEW} ${2 * VIEW}`}
          role="img"
          aria-label="The solar system"
          className="solarsvg"
          preserveAspectRatio="xMidYMid meet"
        >
          <PieceDefs />
          <clipPath id="solarclip">
            <circle cx={CENTER.x} cy={CENTER.y} r={TRACK.radius + 36} />
          </clipPath>
          {/* the base board, cropped to the circle of the solar system and its score track */}
          <image href={assets.board} x={0} y={0} width={BOARD.w} height={BOARD.h} clipPath="url(#solarclip)" />
          {([3, 2, 1] as const).map((n) => {
            const size = DISC[n].size * DISC[n].scale;
            const href = DISCS[n === 3 && s.oumuamua_placed ? "disc-3-oumuamua" : `disc-${n}`];
            return (
              <image
                key={n}
                href={href}
                x={CENTER.x - size / 2 + DISC[n].dx}
                y={CENTER.y - size / 2 + DISC[n].dy}
                width={size}
                height={size}
                className="disc"
                style={{
                  transformBox: "view-box",
                  transformOrigin: `${CENTER.x}px ${CENTER.y}px`,
                  transform: `rotate(${-45 * angle(n)}deg)`,
                }}
              />
            );
          })}
          <image href={assets.sun} x={CENTER.x - SUN_SIZE / 2} y={CENTER.y - SUN_SIZE / 2} width={SUN_SIZE} height={SUN_SIZE} />
          {s.sector_order.map((boardId, position) => {
            const home = STAR_BOARD_HOME[boardId] ?? position;
            const at = QUARTER_AT[home] ?? { x: 0, y: 0 };
            return (
              <image
                key={boardId}
                href={STAR_BOARDS[String(boardId)]}
                x={CENTER.x + at.x}
                y={CENTER.y + at.y}
                width={QUARTER}
                height={QUARTER}
                transform={`rotate(${-(position - home) * 90} ${CENTER.x} ${CENTER.y})`}
              />
            );
          })}
          {probes.map((p, k) => {
            const at = polar(RING_RADIUS[p.ring as number] ?? 270, sectorDegrees(p.sector as number));
            // probes on one space are spread a little, as on the board
            const same = probes.filter((q) => q.ring === p.ring && q.sector === p.sector);
            const i = same.findIndex((q) => q.id === p.id);
            const a = (2 * Math.PI * i) / Math.max(same.length, 1);
            const dx = same.length > 1 ? 46 * Math.cos(a) : 0;
            const dy = same.length > 1 ? 46 * Math.sin(a) : 0;
            const title = `${who(p.player as number)}: ${p.capsule ? "sample capsule" : "probe"}`;
            return p.capsule ? (
              <Marker key={`${p.id}-${k}`} x={at.x + dx} y={at.y + dy} size={78} color={color(p.player as number)} title={title} />
            ) : (
              <ProbePiece key={`${p.id}-${k}`} x={at.x + dx} y={at.y + dy} size={100} color={color(p.player as number)} title={title} />
            );
          })}
        </svg>
        <div className="solarbuttons">
          <button type="button" className="secondary" onClick={() => setCount(0)} disabled={count === 0}>
            Reset to now
          </button>
          <button type="button" className="primary" onClick={() => setCount(count + 1)} disabled={count >= previews.length}>
            Rotate{count > 0 ? ` again (${count} so far)` : ": show the next rotation"}
          </button>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
