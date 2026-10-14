// Places on the board that a move can be made at: where to land or orbit, the sector for a signal, the space for a trace. The engine offers the moves
// and says what each one means (`view.notes`, from move_notes.py); this file only says where on the picture each of them is, so that the board can
// highlight the place and the player can click it. A move that has no place here stays a button of the bar.
import type { View } from "@seti/protocol";
import { ALIEN, ALIEN_COLUMN, ALIEN_TOP, DISCOVERY, MOON, PLANET, RING_BOUNDS, alienColumn, polar } from "./geometry";
import type { Move } from "./moves";
import { SPECIES_SPACES } from "./speciesSpaces";

const TRACE_COLORS = ["pink", "yellow", "blue"];

/** What the engine says about a move (see move_notes.py). */
export type Note = {
  action?: "orbit" | "land";
  planet?: string;
  moon?: string | null;
  free?: boolean;
  cost?: Record<string, number>;
  sector?: number;
  star?: string;
  color?: string;
  slot?: number;
  species?: string | null;
  space?: string;
  rewards?: { t: string; n: number }[];
  alien?: "deck" | "face_up";
  card?: string | null;
} | null;

export type Spot = {
  id: string;
  /** Where it is: a circle, or the outline of a wedge of the star ring. */
  shape:
    | { kind: "circle"; x: number; y: number; r: number }
    | { kind: "path"; d: string }
    | { kind: "rect"; x: number; y: number; w: number; h: number };
  /** The move of the engine that this place stands for, as its place in `view.legal`. */
  move: number;
  label: string;
};

/** The wedge of the star ring that is sector `i`: between the outer ring of the solar system and the outer edge of the stars. */
function sectorPath(i: number): string {
  const [inner, outer] = [(RING_BOUNDS[4] ?? 975) + 12, 1390];
  const a0 = 45 * i;
  const a1 = a0 + 45;
  const p = (r: number, a: number): string => {
    const at = polar(r, a);
    return `${at.x.toFixed(1)} ${at.y.toFixed(1)}`;
  };
  return `M ${p(outer, a0)} A ${outer} ${outer} 0 0 0 ${p(outer, a1)} L ${p(inner, a1)} A ${inner} ${inner} 0 0 1 ${p(inner, a0)} Z`;
}

export const moonKey = (moon: string): string => moon.toLowerCase().split(/[ _]/)[0] ?? "";

/** A place on the picture of a species board, as a place on the base board (the boards sit above it, ALIEN in geometry.ts). */
export const onAlienBoard = (slot: number, x: number, y: number): { x: number; y: number } => ({
  x: (ALIEN.middleX[slot] ?? 680) - ALIEN.centre * ALIEN.scale + x * ALIEN.scale,
  y: ALIEN_TOP + y * ALIEN.scale,
});

export function buildSpots(view: View): { spots: Spot[]; handled: Set<number> } {
  const spots = new Map<string, Spot>();
  const handled = new Set<number>();
  const s = view.state;
  const legal = view.legal as Move[];
  const notes = view.notes as Note[];
  legal.forEach((m, i) => {
    const n = notes[i];
    if (!n) return;
    let spot: Omit<Spot, "move" | "label"> | null = null;
    if (n.alien && n.slot !== undefined) {
      const at = alienColumn(n.slot)[n.alien === "deck" ? "deck" : "faceUp"];
      spot = { id: `alien:${n.slot}:${n.alien}`, shape: { kind: "rect", x: at.x, y: at.y, w: ALIEN_COLUMN.w, h: ALIEN_COLUMN.h } };
    } else if (n.action && n.planet) {
      const st = s.planets[n.planet];
      const pos = PLANET[n.planet];
      if (!st || !pos) return;
      if (n.moon) {
        const at = MOON[moonKey(n.moon)];
        if (at) spot = { id: `moon:${n.moon}`, shape: { kind: "circle", x: at.x, y: at.y + 20, r: 78 } };
      } else if (n.action === "orbit") {
        const k = st.orbiters.length;
        spot = {
          id: `orbit:${n.planet}`,
          shape: { kind: "circle", x: pos.x - pos.r * 0.55 + k * 84, y: pos.y - pos.r * 0.32 + 10, r: 76 },
        };
      } else {
        const k = st.landers.length;
        spot = { id: `land:${n.planet}`, shape: { kind: "circle", x: pos.x - pos.r * 0.55 + k * 84, y: pos.y + pos.r * 0.22 + 20, r: 76 } };
      }
    } else if (n.sector !== undefined) {
      spot = { id: `sector:${n.sector}`, shape: { kind: "path", d: sectorPath(n.sector) } };
    } else if (n.space && n.slot !== undefined && n.color) {
      const kind = n.space;
      const colorIndex = TRACE_COLORS.indexOf(n.color);
      const base = DISCOVERY[n.slot]?.[colorIndex];
      if (kind === "discovery" && base)
        spot = { id: `trace:${n.slot}:discovery:${n.color}`, shape: { kind: "circle", x: base.x, y: base.y, r: 70 } };
      else if (kind === "overflow" && base)
        spot = { id: `trace:${n.slot}:overflow:${n.color}`, shape: { kind: "circle", x: base.x, y: base.y + 190, r: 70 } };
      else if (kind === "board") {
        const species = s.species[n.slot]?.species;
        const at = (species ? SPECIES_SPACES[species]?.[n.color]?.[Number(m.index)] : null) ?? null;
        if (at) {
          const p = onAlienBoard(n.slot, at[0], at[1]);
          spot = { id: `trace:${n.slot}:board:${n.color}:${String(m.index)}`, shape: { kind: "circle", x: p.x, y: p.y, r: 56 } };
        }
      }
    }
    if (!spot) return;
    handled.add(i);
    if (!spots.has(spot.id)) spots.set(spot.id, { ...spot, move: i, label: spot.id });
  });
  return { spots: [...spots.values()], handled };
}
