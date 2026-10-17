"use client";
// A player's marker lying on a circle of a mission card, where the circle has been covered: the same piece as the sector markers of the board,
// in the colour of the owner of the mission. `y` is the height of the circle on the picture, as a fraction (lib/missionCircles.ts).
import type { CSSProperties } from "react";
import { Marker, type PieceColor, PieceDefs } from "./Pieces";

export function CoverMarker({ x, y, color, title }: { x: number; y: number; color: PieceColor; title?: string }) {
  return (
    <svg
      className="covermarker"
      viewBox="-60 -60 120 120"
      style={{ left: `${x * 100}%`, "--y": y } as CSSProperties}
      role="img"
      aria-label={title ?? "covered"}
    >
      <PieceDefs />
      <Marker x={0} y={0} size={100} color={color} title={title} />
    </svg>
  );
}
