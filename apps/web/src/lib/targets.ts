// Places on the board that a move can be made at: where to land or orbit, the sector for a signal, the space for a trace. The engine offers the moves
// and says what each one means (`view.notes`, from move_notes.py); this file only says where on the picture each of them is, so that the board can
// highlight the place and the player can click it. A move that has no place here stays a button of the bar.
import type { View } from "@seti/protocol";
import {
  ALIEN,
  ALIEN_COLUMN,
  ALIEN_TOP,
  DISCOVERY,
  LAND_SPACES,
  MOON,
  OUMUAMUA_TILE,
  PLANET,
  RING_BOUNDS,
  RING_RADIUS,
  alienColumn,
  landSlot,
  orbitSlot,
  polar,
  sectorDegrees,
} from "./geometry";
import { holeAt } from "./glyphids";
import type { Move } from "./moves";
import { SPECIES_SPACES } from "./speciesSpaces";

const TRACE_COLORS = ["pink", "yellow", "blue"];

/** The reward spaces printed on the organization boards of Cosmos Strategy Group and Helion Assembly, in the picture of the card (560 x 421). */
export const ORG_SPACES: Record<string, Record<string, [number, number]>> = {
  cosmos_strategy_group: { credit: [45, 215], publicity: [125, 215], data: [205, 215] },
  helion_assembly: { energy: [40, 130], signal_token: [120, 130], data: [200, 130] },
};

/** The nine organelle spaces of the Amoeba board in its picture (573 x 1044): 6 outer spaces clockwise, 3 inner ones counter-clockwise. */
export const ORGANELLE_SPACES: Record<string, [number, number]> = {
  Y1: [228, 148],
  Y2: [340, 138],
  B1: [478, 355],
  B2: [418, 460],
  P1: [172, 465],
  P2: [112, 353],
  IY: [292, 242],
  IP: [230, 350],
  IB: [350, 335],
};
/** The picture of the Amoeba board is 573 wide; the places of the markers are measured on the species boards of the base board (777 wide). */
export const AMOEBA_SCALE = 573 / 777;

/** What the engine says about a move (see move_notes.py). */
export type Note = {
  /** The move shows something hidden and cannot be taken back: ask for a confirmation first (UNDO-01). */
  irreversible?: boolean;
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
  oumuamua_tile?: boolean;
  /** A first-lander space of a planet and the data it gives (Mars has two, LAND-04). */
  land_data?: { planet: string; slot: number; data: number };
  /** The sector is the one to resolve next (the order of completed sectors, TURN-05). */
  resolve?: boolean;
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
  /** A short text drawn beside the place (the data that a first-lander space of Mars gives). */
  tag?: string;
  /** The place lies on a panel beside the board, in the picture of that panel (not on the board itself). */
  panel?: "glyphids" | "amoeba" | "arkhos" | "org" | "objectives";
  /** What the place holds, for panels that draw it (a glyph token, a chip). */
  glyph?: string;
  /** A hole of the translation board takes several of the player's glyph tokens: the kinds that can be placed there, each with its move (its place in
   * `view.legal`). The player picks one. */
  choices?: { glyph: string; move: number }[];
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
        if (at) spot = { id: `moon:${n.moon}`, shape: { kind: "circle", x: at.x, y: at.y, r: 62 } };
      } else if (n.action === "orbit") {
        const at = orbitSlot(n.planet, st.orbiters.length) ?? { x: pos.x, y: pos.y };
        spot = { id: `orbit:${n.planet}`, shape: { kind: "circle", x: at.x, y: at.y, r: 62 } };
      } else {
        const at = landSlot(n.planet, st.landers.length) ?? pos;
        spot = { id: `land:${n.planet}`, shape: { kind: "circle", x: at.x, y: at.y, r: 62 } };
      }
    } else if (n.land_data) {
      // Mars: the two first-lander spaces, each with its own amount of data, are clicked on the planet
      const at = LAND_SPACES[n.land_data.planet]?.circles[n.land_data.slot];
      if (!at) return;
      spot = {
        id: `landdata:${n.land_data.planet}:${n.land_data.slot}`,
        shape: { kind: "circle", x: at.x, y: at.y, r: 50 },
        tag: `${n.land_data.data} data`,
      };
    } else if (n.oumuamua_tile) {
      // the data slot of the 'Oumuamua tile on disc 3: it turns with the disc (the turn of the disc is in `view.state.disc_angles`)
      const turn = 45 * (s.disc_angles[2] ?? 0);
      const mid = polar(OUMUAMUA_TILE.radius, (OUMUAMUA_TILE.degrees[1] ?? 165) + turn);
      spot = { id: "oumuamua-tile", shape: { kind: "circle", x: mid.x, y: mid.y, r: 135 } };
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
  // the moves of the Space Agencies expansion: they carry their own place, so the engine needs no note for them
  const none = { kind: "circle", x: 0, y: 0, r: 0 } as const;
  const add = (i: number, id: string, shape: Spot["shape"], extra?: Partial<Spot>) => {
    handled.add(i);
    if (!spots.has(id)) spots.set(id, { id, shape, move: i, label: id, ...extra });
  };
  const mineOrg = (view.viewer === null ? null : s.players?.[view.viewer]?.organization) ?? "";
  const first = s.pending?.[0];
  legal.forEach((m, i) => {
    if (m.type === "od_step") {
      // Orbital Dynamics: one step for a probe, to a space next to it
      const to = m.to as [number, number];
      const at = polar(RING_RADIUS[to[0]] ?? 270, sectorDegrees(to[1]));
      add(i, `od:${String(m.probe)}:${to[0]}-${to[1]}`, { kind: "circle", x: at.x, y: at.y, r: 80 });
    } else if (m.type === "decipher") {
      // the holes are on the translation board above the Glyphids board, on the game board itself
      const gi = s.species.findIndex((sp) => sp.discovered && sp.species === "glyphids");
      const at = gi < 0 ? null : holeAt(gi, m.row === "top" ? "top" : "bottom", Number(m.index));
      if (at) {
        const id = `glyph:${String(m.row)}:${String(m.index)}`;
        add(i, id, { ...none, x: at.x, y: at.y, r: 62 });
        const spot = spots.get(id);
        if (spot) spot.choices = [...(spot.choices ?? []), { glyph: String(m.glyph), move: i }];
      }
    } else if (m.type === "pick_organelle") {
      const at = ORGANELLE_SPACES[String(m.space)];
      if (at) add(i, `organelle:${String(m.space)}`, { ...none, x: at[0], y: at[1], r: 40 }, { panel: "amoeba" });
    } else if (m.type === "amoeba_remove") {
      const at = SPECIES_SPACES.amoeba?.[String(m.color)]?.[Number(m.index)];
      if (at)
        add(
          i,
          `amoeba:${String(m.color)}:${String(m.index)}`,
          { ...none, x: at[0] * AMOEBA_SCALE, y: at[1] * AMOEBA_SCALE, r: 34 },
          { panel: "amoeba" },
        );
    } else if (m.type === "mark_objective") {
      add(i, `task:${String(m.objective)}:${String(m.task)}`, { ...none }, { panel: "objectives" });
    } else if (m.type === "org_mark" && ORG_SPACES[mineOrg]?.[String(m.space)]) {
      const at = ORG_SPACES[mineOrg]?.[String(m.space)] ?? [0, 0];
      add(i, `orgspace:${String(m.space)}`, { ...none, x: at[0], y: at[1], r: 34 }, { panel: "org" });
    } else if ((m.type === "org_free" && m.card === undefined) || m.type === "org_main" || m.type === "org_mark" || m.type === "org_skip") {
      add(i, `org:${i}`, { ...none }, { panel: "org" });
    }
  });
  return { spots: [...spots.values()], handled };
}
