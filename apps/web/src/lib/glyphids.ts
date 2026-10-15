// The translation board of the Glyphids (EXP-GLY-02, EXP-GLY-05) as it lies on the game board: attached above the species board, in the one of four
// arrangements that the two random strips give (A-044), with the glyph tokens placed in its holes. Places are in board pixels.
import expansionAssets from "../generated/expansion-assets.json";
import { ALIEN, ALIEN_TOP } from "./geometry";

const ASSET = expansionAssets as Record<string, string>;
/** The picture of the translation board is 750 x 690; its holes (centres) are measured on it. */
export const TRACK_PICTURE = { w: 750, h: 690 };
export const GLYPH_HOLES: Record<"top" | "bottom", [number, number][]> = {
  top: [
    [200, 160],
    [375, 160],
    [545, 160],
  ],
  bottom: [
    [112, 440],
    [290, 440],
    [468, 440],
    [640, 440],
  ],
};
/** The picture of a glyph token (the blue one is named "bue" in the assets). */
export const glyphToken = (glyph: string): string | undefined => ASSET[`tokens/glyphids-token-${glyph === "blue" ? "bue" : glyph}`];

/** The lower edge of the frame in the picture, and how far below the top of the species board that edge lies: the translation board overlaps the top
 * of the species board and nearly touches its top token spaces (the topmost lie 655 px below the top of the board picture). */
const TRACK_EDGE = 682;
const TRACK_BOTTOM_AT = 490;

/** Where the translation board lies on the game board: attached to the top of the Glyphids board in `slot`, as wide as the board. */
export function trackBox(slot: number): { x: number; y: number; w: number; h: number; k: number } {
  const w = ALIEN.w * ALIEN.scale;
  const k = w / TRACK_PICTURE.w;
  const h = TRACK_PICTURE.h * k;
  return { x: (ALIEN.middleX[slot] ?? 680) - ALIEN.centre * ALIEN.scale, y: ALIEN_TOP + TRACK_BOTTOM_AT - TRACK_EDGE * k, w, h, k };
}

/** A hole of the translation board on the game board. */
export function holeAt(slot: number, row: "top" | "bottom", index: number): { x: number; y: number } | null {
  const hole = GLYPH_HOLES[row][index];
  if (!hole) return null;
  const box = trackBox(slot);
  return { x: box.x + hole[0] * box.k, y: box.y + hole[1] * box.k };
}

/**
 * The big slots of the Glyphids board where a glyph token lies (EXP-GLY-03): the upper one above the first space of each column and the lower one
 * above its last; the small spaces under them are for the markers. Measured on the 777 x 1415 picture of the board, by the index of the space.
 */
export const WELL_SLOTS: Record<string, Record<number, [number, number]>> = {
  pink: { 0: [148, 520], 3: [148, 1085] },
  yellow: { 0: [390, 580], 3: [390, 1150] },
  blue: { 0: [630, 515], 3: [630, 1085] },
};
