// Where things are on the base board picture (assets/main-board-assembled.png, 3507 x 5612 px). Every number was measured on that picture:
// the centre is the middle of the sun hole, the rings are the printed circles of the base disc, the score spaces follow the gold spaces
// 25, 50 and 70. Nothing here is a game rule: the engine says where a probe or a marker is, this file only says where that is on the picture.

export const BOARD = { w: 3507, h: 5612 };
export const CENTER = { x: 1752.5, y: 3062.6 };

/** The three discs are scans of different resolution: board pixels per image pixel, and the size of each image. */
export const DISC = {
  1: { scale: 1.886, size: 396 },
  2: { scale: 1.886, size: 608 },
  3: { scale: 1.54, size: 1008 },
} as const;

/** Sector `s` covers 45 s to 45 s + 45 degrees counter-clockwise from the 3 o'clock direction (the engine's convention, BOARD-10). */
export const sectorDegrees = (sector: number): number => 22.5 + 45 * sector;

/** The printed circles that bound ring 1 to 4: from the edge of the sun to the end of ring 1, and so on (a space is the part of a ring in one sector). */
export const RING_BOUNDS = [150, 372, 573, 771, 975];

/** The middle of ring 1 to 4 (index 0 is unused), in board pixels from the centre. */
export const RING_RADIUS = [0, 270, 485, 660, 870];

/** The ring of nearby stars: four boards of two stars (a 1400 px picture cut into four 700 px quarters, drawn at this scale). */
export const STAR = { scale: 2.02, quarter: 700, midRadius: 1193 };
/** Board id -> its position (0 to 3) in the assembled picture of the ring. */
export const STAR_BOARD_HOME: Record<number, number> = { 2: 0, 3: 1, 4: 2, 1: 3 };

export const polar = (radius: number, degrees: number): { x: number; y: number } => ({
  x: CENTER.x + radius * Math.cos((degrees * Math.PI) / 180),
  y: CENTER.y - radius * Math.sin((degrees * Math.PI) / 180),
});

/** The score track: spaces 1 to 100 run clockwise around the board; 0 and 100 share the space at the bottom right. */
export const TRACK = { radius: 1525, degrees50: 145.53, step: 3.592 };
export const scoreDegrees = (score: number): number => TRACK.degrees50 - TRACK.step * ((score % 100 === 0 ? 100 : score % 100) - 50);

/** The publicity track is shown on its own, cut out of the board and turned half a turn (see tools/web/build_assets.py): where the cell of
 * publicity 0 is in that picture (450 x 1270 px) and how far apart the cells are; the players' markers sit side by side. */
export const PUBLICITY_CELL = { x0: 130, dx: 80, y0: 1169, dy: 110.3 };

/** The three big empty circles of the rotation dial, where the moon token lies to mark the disc that turns next. The sequence ring 1, rings 1+2,
 * rings 1+2+3 runs counter-clockwise like the rotation itself: top left (the printed starting space), bottom left, right. */
export const DIAL: Record<1 | 2 | 3, { x: number; y: number }> = {
  1: { x: 2133, y: 4851 },
  2: { x: 2131, y: 5186 },
  3: { x: 2435, y: 5020 },
};
/** The circles are about 216 px wide: the moon token is drawn a little smaller so that the ring of the circle shows. */
export const DIAL_POCKET = 190;

/** The two round pockets printed next to the 20 and the 30 space, where the neutral markers wait (2 of them with 1 or 2 players, 1 with 3, none
 * with 4). The one that is taken first is listed first. */
export const NEUTRAL_POCKETS: Record<"20" | "30", { x: number; y: number }[]> = {
  "20": [
    { x: 1240, y: 4643 },
    { x: 1340, y: 4670 },
  ],
  "30": [
    { x: 406, y: 4037 },
    { x: 468, y: 4118 },
  ],
};

/** The planets: where the picture of each one is, and its radius. Orbiters and landers are drawn on the planet. */
export const PLANET: Record<string, { x: number; y: number; r: number }> = {
  mercury: { x: 379, y: 1678, r: 126 },
  venus: { x: 463, y: 1108, r: 182 },
  mars: { x: 990, y: 1178, r: 168 },
  jupiter: { x: 1537, y: 682, r: 280 },
  saturn: { x: 2236, y: 982, r: 196 },
  uranus: { x: 2960, y: 982, r: 163 },
  neptune: { x: 3058, y: 1543, r: 168 },
};

/** The moons, by the lower-case first word of their name in the engine's data. */
export const MOON: Record<string, { x: number; y: number }> = {
  io: { x: 1871, y: 735 },
  europa: { x: 1838, y: 856 },
  callisto: { x: 1366, y: 1024 },
  ganymede: { x: 1641, y: 1004 },
  enceladus: { x: 2489, y: 996 },
  titan: { x: 2441, y: 1178 },
  titania: { x: 3128, y: 1066 },
  triton: { x: 3198, y: 1762 },
  phobos: { x: 814, y: 1375 },
};

/** The three discovery spaces (pink, yellow, blue) of each alien species: the left group is the first species, the right group the second. */
export const DISCOVERY: { x: number; y: number }[][] = [
  [
    { x: 385, y: 295 },
    { x: 680, y: 370 },
    { x: 975, y: 295 },
  ],
  [
    { x: 2525, y: 295 },
    { x: 2820, y: 370 },
    { x: 3115, y: 295 },
  ],
];

/**
 * The species boards sit above the base board, their three bottom cut-outs around the three discovery spaces of the notch below (the board and
 * its notches are printed so). The picture of a species board is 777 x 1415; its middle cut-out is at x = 388 and the cut-outs are 270 apart.
 */
export const ALIEN = { w: 777, h: 1415, centre: 388, scale: 1.09, bottom: 330, middleX: [680, 2820] };
export const ALIEN_TOP = ALIEN.bottom - ALIEN.h * ALIEN.scale;

/**
 * The four gold scoring tiles lie against the circle of the board on its right side, one after the other, each with its flat lower edge
 * tangent to the circle and its top turned away from the middle of the board. `radius` is the distance from the centre to the outer edge of the
 * board's circle, the tiles are drawn at `scale` of their picture (550 x 488), and the group is centred on `centreDegrees`.
 */
export const GOLD = { w: 550, h: 488, scale: 0.7, radius: 1640, gap: 8, centreDegrees: 2, stepDegrees: 13.6 };

export function goldPlace(i: number): { x: number; y: number; rotation: number } {
  const degrees = GOLD.centreDegrees + (1.5 - i) * GOLD.stepDegrees; // the first tile is the one highest up
  const at = polar(GOLD.radius + GOLD.gap + (GOLD.h * GOLD.scale) / 2, degrees);
  return { x: at.x, y: at.y, rotation: 90 - degrees };
}

/** How far the tiles reach beyond the right edge of the board picture. */
export const GOLD_EXTRA = 300;

/** Where the markers of the choosers sit on a tile (picture of 550 x 488): the first and the second chooser, then the wide space for the others. */
export const GOLD_SLOTS = [
  { x: 105, y: 248 },
  { x: 228, y: 248 },
  { x: 350, y: 248 },
  { x: 425, y: 248 },
];

/**
 * The deck of a discovered species lies in a column to the right of its board: the back of the deck on top (with the number of cards left over it)
 * and the card that lies face up below it. Sizes in board pixels; the column starts `gap` after the right edge of the board.
 */
export const ALIEN_COLUMN = { w: 300, h: 418, gap: 30, between: 36 };

export function alienColumn(slot: number): { deck: { x: number; y: number }; faceUp: { x: number; y: number } } {
  const left = (ALIEN.middleX[slot] ?? 680) - ALIEN.centre * ALIEN.scale;
  const x = left + ALIEN.w * ALIEN.scale + ALIEN_COLUMN.gap;
  const y = ALIEN_TOP + 40;
  return { deck: { x, y }, faceUp: { x, y: y + ALIEN_COLUMN.h + ALIEN_COLUMN.between } };
}

export const PLAYER_COLOR: Record<string, string> = {
  green: "#2fbf71",
  red: "#ff5a52",
  purple: "#a56bff",
  white: "#f3f3f3",
};
export const SECTOR_COLOR: Record<string, string> = { yellow: "#e0b000", red: "#d9503c", blue: "#3b82d6", black: "#3a3f47" };
