// The player pieces, drawn after the photographs in the rulebook (page 2, "Player pieces"): the figure is a small radio dish on a stem and a round
// base (the probe, and with a ring or a base line the orbiter and the lander); the marker is a short cylinder with a dimple, like a bottle cap
// (sector markers, discovery markers); the data token is a blue glossy button; the publicity counter is a microphone-shaped pawn; the score counter is a
// crest with a globe in a laurel wreath. Every piece comes in the four player colours and is shaded to look like the moulded plastic.
// All pieces are drawn in a box from -50 to 50 around the point where they stand; `size` is the width of that box.
import type { ReactNode } from "react";

/** The colours of the pieces by name: the four player colours, a grey for the neutral markers and blue for data. */
export const PIECE_COLORS = {
  green: "#22b565",
  red: "#ef4f48",
  purple: "#8f5cf0",
  white: "#e9edf3",
  neutral: "#8a93a3",
  data: "#2f86e6",
} as const;
export type PieceColor = keyof typeof PIECE_COLORS;

export const pieceColor = (name: string | undefined): PieceColor => (name && name in PIECE_COLORS ? (name as PieceColor) : "white");

function toHsl(hex: string): [number, number, number] {
  const r = Number.parseInt(hex.slice(1, 3), 16) / 255;
  const g = Number.parseInt(hex.slice(3, 5), 16) / 255;
  const b = Number.parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h * 60, s, l];
}

/** The same colour lighter (positive) or darker (negative). */
function shade(hex: string, change: number): string {
  const [h, s, l] = toHsl(hex);
  return `hsl(${Math.round(h)} ${Math.round(s * 100)}% ${Math.round(Math.min(97, Math.max(6, (l + change) * 100)))}%)`;
}

/** Put this once in every SVG that draws pieces. */
export function PieceDefs() {
  return (
    <defs>
      {Object.entries(PIECE_COLORS).map(([name, base]) => (
        <g key={name}>
          <linearGradient id={`pc-${name}-body`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor={shade(base, -0.2)} />
            <stop offset="0.32" stopColor={shade(base, 0.2)} />
            <stop offset="0.62" stopColor={base} />
            <stop offset="1" stopColor={shade(base, -0.28)} />
          </linearGradient>
          <radialGradient id={`pc-${name}-top`} cx="0.35" cy="0.3" r="0.85">
            <stop offset="0" stopColor={shade(base, 0.26)} />
            <stop offset="0.55" stopColor={base} />
            <stop offset="1" stopColor={shade(base, -0.24)} />
          </radialGradient>
          <radialGradient id={`pc-${name}-dimple`} cx="0.5" cy="0.6" r="0.7">
            <stop offset="0" stopColor={shade(base, -0.3)} />
            <stop offset="0.7" stopColor={shade(base, -0.12)} />
            <stop offset="1" stopColor={shade(base, 0.12)} />
          </radialGradient>
        </g>
      ))}
    </defs>
  );
}

const edge = (color: PieceColor): string => shade(PIECE_COLORS[color], -0.36);
const gradient = (color: PieceColor, kind: "body" | "top" | "dimple"): string => `url(#pc-${color}-${kind})`;

function Piece({ x, y, size, title, children }: { x: number; y: number; size: number; title?: string; children: ReactNode }) {
  return (
    // a CSS transform, so that a piece that is given a new place glides there (`.piece` in game.css) instead of jumping
    <g className="piece" style={{ transform: `translate(${x}px, ${y}px) scale(${size / 100})` }}>
      {children}
      {title ? <title>{title}</title> : null}
    </g>
  );
}

/** A marker: a short cylinder with a dimple, seen from above. */
export function Marker({ x, y, size = 56, color, title }: { x: number; y: number; size?: number; color: PieceColor; title?: string }) {
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <ellipse cy={9} rx={44} ry={38} fill={edge(color)} />
      <ellipse rx={44} ry={38} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={4} />
      <ellipse rx={29} ry={24} fill={gradient(color, "dimple")} stroke={edge(color)} strokeWidth={2} />
      <path d="M-34 -14 A40 33 0 0 1 4 -35" fill="none" stroke="#fff" strokeOpacity={0.55} strokeWidth={5} strokeLinecap="round" />
    </Piece>
  );
}

/** A figure: a radio dish on a stem and a round base. */
export function Figure({ x, y, size = 104, color, title }: { x: number; y: number; size?: number; color: PieceColor; title?: string }) {
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <ellipse cy={42} rx={28} ry={9} fill={edge(color)} />
      <ellipse cy={37} rx={26} ry={9} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={3} />
      <rect x={-6} y={-4} width={12} height={42} fill={gradient(color, "body")} stroke={edge(color)} strokeWidth={2} />
      <g transform="rotate(-24 0 -14)">
        <ellipse cy={-14} rx={41} ry={27} fill={edge(color)} />
        <ellipse cy={-17} rx={40} ry={26} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={3} />
        <ellipse cy={-17} rx={30} ry={18} fill={gradient(color, "dimple")} />
        <path d="M0 -19 L13 -45" stroke={edge(color)} strokeWidth={4} strokeLinecap="round" />
        <circle cx={13} cy={-46} r={5} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={2} />
      </g>
    </Piece>
  );
}

/** A space probe: a round token (so that it fits the orbit and landing spaces) with a satellite on it: a body with two solar panels on the diagonal and a
 * dish that sends out signals. */
export function ProbePiece({ x, y, size = 104, color, title }: { x: number; y: number; size?: number; color: PieceColor; title?: string }) {
  const ink = "#fff";
  const line = edge(color);
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <circle cy={7} r={45} fill={line} />
      <circle r={45} fill={gradient(color, "top")} stroke={line} strokeWidth={4} />
      <circle r={37} fill={gradient(color, "dimple")} stroke={line} strokeWidth={2} />
      <g transform="rotate(45)" stroke={line} strokeWidth={2.2} strokeLinejoin="round" strokeLinecap="round">
        {/* the two solar panels, with their cells */}
        <rect x={-33} y={-8} width={21} height={16} rx={1.5} fill={ink} fillOpacity={0.95} />
        <rect x={12} y={-8} width={21} height={16} rx={1.5} fill={ink} fillOpacity={0.95} />
        <path d="M-26 -8 V8 M-19 -8 V8 M-33 0 H-12 M19 -8 V8 M26 -8 V8 M12 0 H33" strokeWidth={1.4} />
        <path d="M-12 0 H12" strokeWidth={3} />
        {/* the body with its round window */}
        <rect x={-10} y={-7} width={20} height={14} rx={3} fill={ink} />
        <circle r={3.2} fill={line} stroke="none" />
        {/* the dish on top of the body, and the signal it sends */}
        <path d="M-6 -8 L-4 -12" />
        <path d="M-9 -13 Q0 -22 9 -13 Z" fill={ink} />
        <path d="M-5 -24 Q0 -28 5 -24" fill="none" strokeWidth={1.8} />
        <path d="M-9 -29 Q0 -35 9 -29" fill="none" strokeWidth={1.8} />
      </g>
    </Piece>
  );
}

/** The publicity counter: a microphone-shaped pawn. */
export function PublicityPawn({
  x,
  y,
  size = 96,
  color,
  title,
}: { x: number; y: number; size?: number; color: PieceColor; title?: string }) {
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <ellipse cy={44} rx={26} ry={8} fill={edge(color)} />
      <ellipse cy={39} rx={24} ry={8} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={3} />
      <rect x={-9} y={12} width={18} height={28} fill={gradient(color, "body")} stroke={edge(color)} strokeWidth={2} />
      <rect x={-21} y={-47} width={42} height={66} rx={21} fill={gradient(color, "body")} stroke={edge(color)} strokeWidth={3} />
      <path d="M-21 -27 H21 M-21 -12 H21" stroke={edge(color)} strokeOpacity={0.6} strokeWidth={3} />
      <rect x={-14} y={-41} width={7} height={48} rx={3.5} fill="#fff" fillOpacity={0.4} />
    </Piece>
  );
}

/** The score counter: a crest with a globe in a laurel wreath, on a stepped base. */
export function ScorePawn({ x, y, size = 92, color, title }: { x: number; y: number; size?: number; color: PieceColor; title?: string }) {
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <rect x={-28} y={30} width={56} height={14} rx={3} fill={gradient(color, "body")} stroke={edge(color)} strokeWidth={3} />
      <rect x={-21} y={19} width={42} height={13} rx={3} fill={gradient(color, "body")} stroke={edge(color)} strokeWidth={3} />
      <path d="M-30 -18 A34 34 0 0 0 -9 20" fill="none" stroke={edge(color)} strokeWidth={13} strokeLinecap="round" />
      <path d="M30 -18 A34 34 0 0 1 9 20" fill="none" stroke={edge(color)} strokeWidth={13} strokeLinecap="round" />
      <path d="M-30 -18 A34 34 0 0 0 -9 20" fill="none" stroke={gradient(color, "body")} strokeWidth={8} strokeLinecap="round" />
      <path d="M30 -18 A34 34 0 0 1 9 20" fill="none" stroke={gradient(color, "body")} strokeWidth={8} strokeLinecap="round" />
      <circle cy={-8} r={23} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={3} />
      <path d="M-14 -16 Q-2 -26 10 -18" fill="none" stroke="#fff" strokeOpacity={0.55} strokeWidth={4} strokeLinecap="round" />
    </Piece>
  );
}

/** A data token: a blue glossy button with a ring and three bars of data on it. */
export function DataToken({ x, y, size = 52, title }: { x: number; y: number; size?: number; title?: string }) {
  const color: PieceColor = "data";
  return (
    <Piece x={x} y={y} size={size} title={title}>
      <circle cy={8} r={44} fill={edge(color)} />
      <circle r={44} fill={gradient(color, "top")} stroke={edge(color)} strokeWidth={4} />
      <circle r={34} fill="none" stroke="#fff" strokeOpacity={0.55} strokeWidth={3} />
      <circle r={30} fill={gradient(color, "dimple")} />
      <path d="M-15 -11 H15 M-15 0 H7 M-15 11 H11" stroke="#fff" strokeOpacity={0.9} strokeWidth={6} strokeLinecap="round" />
      <path d="M-33 -14 A38 38 0 0 1 -6 -36" fill="none" stroke="#fff" strokeOpacity={0.6} strokeWidth={5} strokeLinecap="round" />
    </Piece>
  );
}
