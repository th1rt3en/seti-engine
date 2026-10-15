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
// the four arrangements: [top strip side, bottom strip side] -> the picture (a to d)
const VARIANT: Record<string, string> = { "0,0": "a", "1,1": "b", "1,0": "c", "0,1": "d" };

/** The picture of the translation board for the sides of the two strips. */
export function trackPicture(sides: number[] | undefined): string | undefined {
  return ASSET[`boards/glyphids-track-${VARIANT[(sides ?? [0, 0]).join(",")] ?? "a"}`];
}

/** The picture of a glyph token (the blue one is named "bue" in the assets). */
export const glyphToken = (glyph: string): string | undefined => ASSET[`tokens/glyphids-token-${glyph === "blue" ? "bue" : glyph}`];

/** Where the translation board lies on the game board: above the Glyphids board in `slot`, as wide as the board. */
export function trackBox(slot: number): { x: number; y: number; w: number; h: number; k: number } {
  const w = ALIEN.w * ALIEN.scale;
  const k = w / TRACK_PICTURE.w;
  const h = TRACK_PICTURE.h * k;
  return { x: (ALIEN.middleX[slot] ?? 680) - ALIEN.centre * ALIEN.scale, y: ALIEN_TOP - h, w, h, k };
}

/** A hole of the translation board on the game board. */
export function holeAt(slot: number, row: "top" | "bottom", index: number): { x: number; y: number } | null {
  const hole = GLYPH_HOLES[row][index];
  if (!hole) return null;
  const box = trackBox(slot);
  return { x: box.x + hole[0] * box.k, y: box.y + hole[1] * box.k };
}
